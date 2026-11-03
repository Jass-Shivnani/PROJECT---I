/**
 * Dione AI — Client-Side Neural Audio & Live Full-Duplex Engine
 * ==============================================================
 * 1. Connects to `/api/audio/live` WebSocket (Gemini Live Aoede 24kHz PCM).
 * 2. Gapless Web Audio playback queue for 24kHz 16-bit PCM chunks.
 * 3. 16kHz PCM microphone capture with Client-side VAD (Voice Activity Detection).
 * 4. Barge-in interruption: user speech immediately halts model playback.
 * 5. Real-time audio RMS telemetry for the VisionOS pulsating neural iris.
 */

export interface NeuralAudioCallbacks {
  onStateChange: (state: {
    isConnected: boolean;
    isListening: boolean;
    isSpeaking: boolean;
    volume: number; // 0.0 to 1.0 for pulsating iris
    statusText: string;
  }) => void;
  onTranscript?: (text: string, isUser: boolean) => void;
  onError?: (err: string) => void;
}

export class NeuralAudioClient {
  private ws: WebSocket | null = null;
  private audioCtxOut: AudioContext | null = null;
  private analyserOut: AnalyserNode | null = null;
  private nextPlayTime: number = 0;
  private activeSources: AudioBufferSourceNode[] = [];

  // Mic & VAD
  private micStream: MediaStream | null = null;
  private audioCtxIn: AudioContext | null = null;
  private processorIn: ScriptProcessorNode | null = null;
  private analyserIn: AnalyserNode | null = null;

  // VAD thresholds
  private vadThreshold = 0.006; // Highly responsive RMS sensitivity for conversational speech
  private isSpeakingLocally = false;
  private silenceFrames = 0;
  private speechFrames = 0;

  private isConnected = false;
  private isListening = false;
  private isModelSpeaking = false;
  private animFrameId: number | null = null;

  private callbacks: NeuralAudioCallbacks;

  constructor(callbacks: NeuralAudioCallbacks) {
    this.callbacks = callbacks;
  }

  public async connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const loc = window.location;
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${loc.host}/api/audio/live`;

    this.callbacks.onStateChange({
      isConnected: false,
      isListening: false,
      isSpeaking: false,
      volume: 0,
      statusText: 'Connecting to Gemini Live Aoede voice...',
    });

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = async () => {
        this.isConnected = true;
        await this._initAudioOut();
        await this._startMicCapture();
        this._startVolumeMeter();

        this.callbacks.onStateChange({
          isConnected: true,
          isListening: true,
          isSpeaking: false,
          volume: 0,
          statusText: 'Live neural voice connected · Listening',
        });
      };

      this.ws.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
          // 24kHz PCM binary frame from Gemini Live
          await this._queuePcmChunk(event.data);
        } else if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'transcript') {
              this.callbacks.onTranscript?.(data.text || '', data.role === 'user');
            } else if (data.type === 'turn_complete') {
              // Model turn completed
            } else if (data.type === 'session_ready') {
              this.callbacks.onStateChange({
                isConnected: true,
                isListening: true,
                isSpeaking: false,
                volume: 0,
                statusText: `Aoede Neural Voice Ready (${data.voice || 'Aoede'})`,
              });
            } else if (data.type === 'error') {
              this.callbacks.onError?.(data.message || 'Live audio error');
            }
          } catch {}
        }
      };

      this.ws.onerror = (err) => {
        console.error('Neural Audio WS error:', err);
        this.callbacks.onError?.('Failed to connect to Live Voice service');
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.isListening = false;
        this.isModelSpeaking = false;
        this._stopMicCapture();
        this._cancelVolumeMeter();
        this.callbacks.onStateChange({
          isConnected: false,
          isListening: false,
          isSpeaking: false,
          volume: 0,
          statusText: 'Neural voice disconnected',
        });
      };
    } catch (e: any) {
      this.callbacks.onError?.(e.message || 'WebSocket connection error');
    }
  }

  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._stopMicCapture();
    this.interruptPlayback();
    this._cancelVolumeMeter();
    this.isConnected = false;
    this.isListening = false;
    this.isModelSpeaking = false;

    this.callbacks.onStateChange({
      isConnected: false,
      isListening: false,
      isSpeaking: false,
      volume: 0,
      statusText: 'Disconnected',
    });
  }

  public sendTextPrompt(text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'text_prompt', text }));
    }
  }

  public interruptPlayback(): void {
    for (const src of this.activeSources) {
      try {
        src.stop();
        src.disconnect();
      } catch {}
    }
    this.activeSources = [];
    if (this.audioCtxOut) {
      this.nextPlayTime = this.audioCtxOut.currentTime;
    }
    this.isModelSpeaking = false;
  }

  // -------------------------------------------------------------
  // Audio Out: 24kHz PCM Playback
  // -------------------------------------------------------------
  private async _initAudioOut(): Promise<void> {
    if (!this.audioCtxOut || this.audioCtxOut.state === 'closed') {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtxOut = new AudioContextClass();
      this.analyserOut = this.audioCtxOut.createAnalyser();
      this.analyserOut.fftSize = 256;
      this.analyserOut.connect(this.audioCtxOut.destination);
      this.nextPlayTime = this.audioCtxOut.currentTime;
    }
    if (this.audioCtxOut.state === 'suspended') {
      await this.audioCtxOut.resume();
    }
  }

  private async _queuePcmChunk(arrayBuffer: ArrayBuffer): Promise<void> {
    if (!this.audioCtxOut || this.audioCtxOut.state === 'closed') {
      await this._initAudioOut();
    }
    if (!this.audioCtxOut || !this.analyserOut) return;

    // Convert 16-bit PCM Little Endian to Float32
    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }

    const audioBuffer = this.audioCtxOut.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);

    const source = this.audioCtxOut.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.analyserOut);

    const now = this.audioCtxOut.currentTime;
    const startTime = Math.max(now, this.nextPlayTime);
    source.start(startTime);
    this.nextPlayTime = startTime + audioBuffer.duration;

    this.activeSources.push(source);
    this.isModelSpeaking = true;

    source.onended = () => {
      const idx = this.activeSources.indexOf(source);
      if (idx !== -1) this.activeSources.splice(idx, 1);
      if (this.activeSources.length === 0) {
        this.isModelSpeaking = false;
      }
    };
  }

  // -------------------------------------------------------------
  // Audio In: 16kHz PCM Capture + Client-Side VAD
  // -------------------------------------------------------------
  private async _startMicCapture(): Promise<void> {
    try {
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtxIn = new AudioContextClass();
      if (this.audioCtxIn.state === 'suspended') {
        await this.audioCtxIn.resume();
      }
      const actualSampleRate = this.audioCtxIn.sampleRate;
      const micSource = this.audioCtxIn.createMediaStreamSource(this.micStream);

      this.analyserIn = this.audioCtxIn.createAnalyser();
      this.analyserIn.fftSize = 256;

      // 4096 buffer size
      this.processorIn = this.audioCtxIn.createScriptProcessor(4096, 1, 1);

      this.processorIn.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);

        // 1. Calculate RMS volume
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        // 2. Client-Side VAD Logic
        if (rms >= this.vadThreshold) {
          this.speechFrames++;
          this.silenceFrames = 0;

          if (this.speechFrames >= 2) {
            // User confirmed speaking
            if (!this.isSpeakingLocally) {
              this.isSpeakingLocally = true;
              // Barge-in: immediately silence model if it was speaking!
              if (this.isModelSpeaking) {
                this.interruptPlayback();
              }
            }
          }
        } else {
          this.silenceFrames++;
          if (this.silenceFrames >= 8) { // ~800ms silence
            if (this.isSpeakingLocally) {
              this.isSpeakingLocally = false;
              this.speechFrames = 0;
              // Notify backend that user finished turn
              if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'end_of_turn' }));
              }
            }
          }
        }

        // 3. Downsample to 16kHz PCM and transmit if user is active
        if (this.isSpeakingLocally || this.silenceFrames < 3) {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const pcm16 = this._downsampleTo16k(inputData, actualSampleRate);
            this.ws.send(pcm16.buffer as ArrayBuffer);
          }
        }
      };

      micSource.connect(this.analyserIn);
      this.analyserIn.connect(this.processorIn);

      // Prevent mic monitor feedback loop into speakers
      const muteGain = this.audioCtxIn.createGain();
      muteGain.gain.value = 0;
      this.processorIn.connect(muteGain);
      muteGain.connect(this.audioCtxIn.destination);
    } catch (err: any) {
      console.warn('Microphone permission or capture error:', err);
      this.callbacks.onError?.(`Microphone access error: ${err.message || err}`);
    }
  }

  private _downsampleTo16k(inputBuffer: Float32Array, inputSampleRate: number): Int16Array {
    if (inputSampleRate === 16000) {
      const pcm16 = new Int16Array(inputBuffer.length);
      for (let i = 0; i < inputBuffer.length; i++) {
        const s = Math.max(-1, Math.min(1, inputBuffer[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      return pcm16;
    }
    const ratio = inputSampleRate / 16000;
    const newLength = Math.round(inputBuffer.length / ratio);
    const result = new Int16Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < inputBuffer.length; i++) {
        accum += inputBuffer[i];
        count++;
      }
      const sample = count > 0 ? accum / count : inputBuffer[offsetBuffer];
      const s = Math.max(-1, Math.min(1, sample));
      result[offsetResult] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  private _stopMicCapture(): void {
    if (this.processorIn) {
      this.processorIn.disconnect();
      this.processorIn = null;
    }
    if (this.analyserIn) {
      this.analyserIn.disconnect();
      this.analyserIn = null;
    }
    if (this.audioCtxIn) {
      this.audioCtxIn.close();
      this.audioCtxIn = null;
    }
    if (this.micStream) {
      this.micStream.getTracks().forEach((t) => t.stop());
      this.micStream = null;
    }
    this.isSpeakingLocally = false;
  }

  // -------------------------------------------------------------
  // Live Audio Telemetry for VisionOS Neural Iris
  // -------------------------------------------------------------
  private _startVolumeMeter(): void {
    const update = () => {
      let vol = 0;

      if (this.isModelSpeaking && this.analyserOut) {
        const data = new Uint8Array(this.analyserOut.frequencyBinCount);
        this.analyserOut.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        vol = Math.min(1.0, (sum / data.length) / 90.0);
      } else if (this.isSpeakingLocally && this.analyserIn) {
        const data = new Uint8Array(this.analyserIn.frequencyBinCount);
        this.analyserIn.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        vol = Math.min(1.0, (sum / data.length) / 80.0);
      }

      this.callbacks.onStateChange({
        isConnected: this.isConnected,
        isListening: this.isListening,
        isSpeaking: this.isModelSpeaking,
        volume: vol,
        statusText: this.isModelSpeaking
          ? 'Dione speaking (Aoede Voice)...'
          : this.isSpeakingLocally
          ? 'Listening to your voice...'
          : 'Live Neural Voice Active',
      });

      this.animFrameId = requestAnimationFrame(update);
    };

    this.animFrameId = requestAnimationFrame(update);
  }

  private _cancelVolumeMeter(): void {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }
}
