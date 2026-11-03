/**
 * Dione AI — Client-Side Neural Audio & Live Full-Duplex Engine (v3.0 Overhaul)
 * =============================================================================
 * 1. Connects to `/api/audio/live` WebSocket (Gemini Live + Gemini 3.8 Extended Thinking + DioneEngine tools).
 * 2. Hardware Microphone & Speaker device enumeration and live hot-swapping (`deviceId: { exact }`).
 * 3. Gapless Web Audio playback queue for 24kHz 16-bit PCM chunks.
 * 4. 16kHz PCM microphone capture with Client-side VAD & barge-in interruption.
 */

export interface AudioDeviceOption {
  deviceId: string;
  label: string;
  kind: 'audioinput' | 'audiooutput';
}

export interface NeuralAudioCallbacks {
  onStateChange: (state: {
    isConnected: boolean;
    isListening: boolean;
    isSpeaking: boolean;
    volume: number;
    statusText: string;
    selectedMicId?: string;
  }) => void;
  onTranscript?: (text: string, isUser: boolean) => void;
  onThought?: (thoughtText: string, model: string) => void;
  onError?: (err: string) => void;
}

const STORAGE_KEY_MIC_ID = 'dione_selected_mic_device_id_v1';
const STORAGE_KEY_SPEAKER_ID = 'dione_selected_speaker_device_id_v1';

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

  private selectedMicId: string = localStorage.getItem(STORAGE_KEY_MIC_ID) || '';
  private selectedSpeakerId: string = localStorage.getItem(STORAGE_KEY_SPEAKER_ID) || '';

  private vadThreshold = 0.015;
  private isSpeakingLocally = false;
  private silenceFrames = 0;
  private speechFrames = 0;

  private isConnected = false;
  private isListening = false;
  private isModelSpeaking = false;
  private currentStatusOverride: string = '';
  private animFrameId: number | null = null;

  private callbacks: NeuralAudioCallbacks;

  constructor(callbacks: NeuralAudioCallbacks) {
    this.callbacks = callbacks;
  }

  public getSelectedMicId(): string {
    return this.selectedMicId;
  }

  public getSelectedSpeakerId(): string {
    return this.selectedSpeakerId;
  }

  public static async getAudioDevices(): Promise<{ inputs: AudioDeviceOption[]; outputs: AudioDeviceOption[] }> {
    try {
      if (!navigator.mediaDevices?.enumerateDevices) {
        return { inputs: [], outputs: [] };
      }
      let devices = await navigator.mediaDevices.enumerateDevices();
      const hasLabels = devices.some(d => d.kind === 'audioinput' && d.label);
      if (!hasLabels) {
        try {
          const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          tempStream.getTracks().forEach(t => t.stop());
          devices = await navigator.mediaDevices.enumerateDevices();
        } catch {
          // User hasn't granted permission yet
        }
      }

      const inputs: AudioDeviceOption[] = [];
      const outputs: AudioDeviceOption[] = [];

      devices.forEach((d, idx) => {
        if (d.kind === 'audioinput' && d.deviceId) {
          inputs.push({
            deviceId: d.deviceId,
            label: d.label || `Microphone ${idx + 1}`,
            kind: 'audioinput',
          });
        } else if (d.kind === 'audiooutput' && d.deviceId) {
          outputs.push({
            deviceId: d.deviceId,
            label: d.label || `Speaker ${idx + 1}`,
            kind: 'audiooutput',
          });
        }
      });

      return { inputs, outputs };
    } catch (e) {
      console.warn('Failed to enumerate audio devices:', e);
      return { inputs: [], outputs: [] };
    }
  }

  public async setMicDevice(deviceId: string): Promise<void> {
    this.selectedMicId = deviceId;
    try {
      localStorage.setItem(STORAGE_KEY_MIC_ID, deviceId);
    } catch {}

    // Hot-swap active microphone stream if currently connected
    if (this.isConnected) {
      this._stopMicCapture();
      await this._startMicCapture();
    }
  }

  public async setSpeakerDevice(deviceId: string): Promise<void> {
    this.selectedSpeakerId = deviceId;
    try {
      localStorage.setItem(STORAGE_KEY_SPEAKER_ID, deviceId);
    } catch {}

    if (this.audioCtxOut && typeof (this.audioCtxOut as any).setSinkId === 'function' && deviceId) {
      try {
        await (this.audioCtxOut as any).setSinkId(deviceId);
      } catch (e) {
        console.warn('setSinkId not supported on this browser/device:', e);
      }
    }
  }

  public async connect(micDeviceId?: string): Promise<void> {
    if (micDeviceId !== undefined) {
      this.selectedMicId = micDeviceId;
      try {
        localStorage.setItem(STORAGE_KEY_MIC_ID, micDeviceId);
      } catch {}
    }

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
      statusText: 'Connecting to Gemini Live + 3.8 Extended Thinking...',
      selectedMicId: this.selectedMicId,
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
          statusText: 'Live Voice + Gemini 3.8 Thinking Active',
          selectedMicId: this.selectedMicId,
        });
      };

      this.ws.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
          await this._queuePcmChunk(event.data);
        } else if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'transcript') {
              this.currentStatusOverride = '';
              this.callbacks.onTranscript?.(data.text || '', data.role === 'user');
            } else if (data.type === 'thought') {
              this.callbacks.onThought?.(data.text || '', data.model || 'gemini-3.8-flash');
            } else if (data.type === 'status') {
              this.currentStatusOverride = data.text || '';
            } else if (data.type === 'turn_complete') {
              this.currentStatusOverride = '';
            } else if (data.type === 'session_ready') {
              this.callbacks.onStateChange({
                isConnected: true,
                isListening: true,
                isSpeaking: false,
                volume: 0,
                statusText: `Live Ready (${data.voice || 'Aoede'} + ${data.reasoning_model || 'Gemini 3.8'})`,
                selectedMicId: this.selectedMicId,
              });
            } else if (data.type === 'error') {
              this.callbacks.onError?.(data.message || 'Live audio error');
            }
          } catch {}
        }
      };

      this.ws.onerror = () => {
        this.callbacks.onError?.('Failed to connect to Live Voice service');
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.isListening = false;
        this.isModelSpeaking = false;
        this.currentStatusOverride = '';
        this._stopMicCapture();
        this._cancelVolumeMeter();
        this.callbacks.onStateChange({
          isConnected: false,
          isListening: false,
          isSpeaking: false,
          volume: 0,
          statusText: 'Voice Disconnected',
          selectedMicId: this.selectedMicId,
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
    this.currentStatusOverride = '';

    this.callbacks.onStateChange({
      isConnected: false,
      isListening: false,
      isSpeaking: false,
      volume: 0,
      statusText: 'Disconnected',
      selectedMicId: this.selectedMicId,
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

  private async _initAudioOut(): Promise<void> {
    if (!this.audioCtxOut || this.audioCtxOut.state === 'closed') {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtxOut = new AudioContextClass();
      if (this.selectedSpeakerId && typeof (this.audioCtxOut as any).setSinkId === 'function') {
        try {
          await (this.audioCtxOut as any).setSinkId(this.selectedSpeakerId);
        } catch {}
      }
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

  private async _startMicCapture(): Promise<void> {
    try {
      const audioConstraints: MediaTrackConstraints = {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };

      if (this.selectedMicId && this.selectedMicId !== 'default') {
        audioConstraints.deviceId = { exact: this.selectedMicId };
      }

      try {
        this.micStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      } catch {
        // Fallback to any available microphone if exact deviceId was unplugged
        this.micStream = await navigator.mediaDevices.getUserMedia({
          audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      }

      const activeTrack = this.micStream.getAudioTracks()[0];
      if (activeTrack) {
        const settings = activeTrack.getSettings();
        if (settings.deviceId) {
          this.selectedMicId = settings.deviceId;
        }
      }

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtxIn = new AudioContextClass();
      if (this.audioCtxIn.state === 'suspended') {
        await this.audioCtxIn.resume();
      }
      const actualSampleRate = this.audioCtxIn.sampleRate;
      const micSource = this.audioCtxIn.createMediaStreamSource(this.micStream);

      this.analyserIn = this.audioCtxIn.createAnalyser();
      this.analyserIn.fftSize = 256;

      this.processorIn = this.audioCtxIn.createScriptProcessor(4096, 1, 1);

      this.processorIn.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);

        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        // When the model is speaking, require louder speech (0.05) to avoid speaker echo interrupting playback
        const activeThreshold = this.isModelSpeaking ? 0.05 : this.vadThreshold;

        if (rms >= activeThreshold) {
          this.speechFrames++;
          this.silenceFrames = 0;

          if (this.speechFrames >= 3) {
            if (!this.isSpeakingLocally) {
              this.isSpeakingLocally = true;
              if (this.isModelSpeaking) {
                // User intentionally spoke loudly over the model to interrupt
                this.interruptPlayback();
              }
            }
          }
        } else {
          this.silenceFrames++;
          if (this.silenceFrames >= 16) {
            if (this.isSpeakingLocally) {
              this.isSpeakingLocally = false;
              this.speechFrames = 0;
              if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'end_of_turn' }));
              }
            }
          }
        }

        if (this.isSpeakingLocally || this.silenceFrames < 3) {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const pcm16 = this._downsampleTo16k(inputData, actualSampleRate);
            this.ws.send(pcm16.buffer as ArrayBuffer);
          }
        }
      };

      micSource.connect(this.analyserIn);
      this.analyserIn.connect(this.processorIn);

      const muteGain = this.audioCtxIn.createGain();
      muteGain.gain.value = 0;
      this.processorIn.connect(muteGain);
      muteGain.connect(this.audioCtxIn.destination);
      this.isListening = true;
    } catch (err: any) {
      console.warn('Microphone capture error:', err);
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

  private _startVolumeMeter(): void {
    const update = () => {
      let vol = 0;

      if (this.isModelSpeaking && this.analyserOut) {
        const data = new Uint8Array(this.analyserOut.frequencyBinCount);
        this.analyserOut.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        vol = Math.min(1.0, (sum / data.length) / 90.0);
      } else if (this.analyserIn) {
        const data = new Uint8Array(this.analyserIn.frequencyBinCount);
        this.analyserIn.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        vol = Math.min(1.0, (sum / data.length) / 80.0);
      }

      const statusText =
        this.currentStatusOverride ||
        (this.isModelSpeaking
          ? 'Dione speaking...'
          : this.isSpeakingLocally
          ? 'Listening to your voice...'
          : 'Live Voice + Gemini 3.8 Ready');

      this.callbacks.onStateChange({
        isConnected: this.isConnected,
        isListening: this.isListening,
        isSpeaking: this.isModelSpeaking,
        volume: vol,
        statusText,
        selectedMicId: this.selectedMicId,
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
