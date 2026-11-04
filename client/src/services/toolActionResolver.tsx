import React from 'react';
import {
  Play,
  Maximize2,
  Camera,
  Globe,
  AppWindow,
  Sparkles,
  Gamepad2,
  Search,
  Bookmark,
  Cpu,
  Clock,
  SquareX,
  Terminal,
  MousePointer,
  Keyboard,
  FileText,
  Volume2,
  Layers
} from 'lucide-react';
import { ToolCall } from '../types';

export interface ResolvedAction {
  title: string;
  category:
    | 'media'
    | 'keyboard'
    | 'vision'
    | 'browser'
    | 'window'
    | 'game'
    | 'search'
    | 'memory'
    | 'system'
    | 'process'
    | 'mouse'
    | 'terminal';
  icon: React.ReactNode;
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
  isPowerShellOrCli: boolean;
  cleanCommandSummary?: string;
}

/**
 * Resolves raw tool calls into user-friendly semantic representations.
 * Specially converts known PowerShell/CLI/Python automation commands into friendly labels and semantic icons.
 */
export function resolveToolAction(toolCall: ToolCall): ResolvedAction {
  const tool = (toolCall.tool || '').toLowerCase();
  const params = toolCall.params || {};
  const rawCmd = typeof params.command === 'string' ? params.command : '';
  const cmdLower = rawCmd.toLowerCase();

  // Helper to extract query parameter from URL
  const extractQuery = (str: string): string => {
    try {
      const match = str.match(/search_query=([^&"'\s]+)/);
      if (match && match[1]) {
        return decodeURIComponent(match[1].replace(/\+/g, ' '));
      }
    } catch {
      // ignore
    }
    return '';
  };


  // 0. Smart Multi-Step Task Planner & External Service Integrations
  if (tool === 'plan_task_workflow') {
    const goalStr = params.goal || 'Multi-Service Objective';
    return {
      title: `Task Plan: ${goalStr.length > 42 ? goalStr.slice(0, 42) + '...' : goalStr}`,
      category: 'system',
      icon: <Layers className="w-3.5 h-3.5" />,
      badgeBg: 'bg-violet-500/20',
      badgeBorder: 'border-violet-500/30',
      badgeText: 'text-violet-300',
      isPowerShellOrCli: false,
    };
  }

  // 0A. Hermes Programmatic Tool Calling & Execution Sandbox
  if (tool === 'execute_code') {
    return {
      title: 'Hermes PTC: Python Sandbox Execution',
      category: 'terminal',
      icon: <Terminal className="w-3.5 h-3.5" />,
      badgeBg: 'bg-emerald-500/20',
      badgeBorder: 'border-emerald-500/30',
      badgeText: 'text-emerald-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool === 'todo' || tool === 'delegate_task') {
    return {
      title: `Hermes Agent: ${tool.replace('_', ' ').toUpperCase()}`,
      category: 'system',
      icon: <Layers className="w-3.5 h-3.5" />,
      badgeBg: 'bg-indigo-500/20',
      badgeBorder: 'border-indigo-500/30',
      badgeText: 'text-indigo-300',
      isPowerShellOrCli: false,
    };
  }

  // 0B. Drawing & Canvas Manipulation Primitives
  if (tool === 'computer_draw_shape' || tool === 'computer_draw_circle' || tool === 'computer_drag') {
    const shape = params.shape || (tool.includes('circle') ? 'circle' : 'drag');
    return {
      title: `Canvas Draw: ${shape.toUpperCase()} (Win32 Path)`,
      category: 'mouse',
      icon: <Sparkles className="w-3.5 h-3.5" />,
      badgeBg: 'bg-pink-500/20',
      badgeBorder: 'border-pink-500/30',
      badgeText: 'text-pink-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool.includes('gmail') || tool === 'send_email' || tool === 'read_emails') {
    const recipient = params.to || '';
    const isSend = tool.includes('send');
    return {
      title: isSend ? `Gmail Send -> ${recipient || 'Recipient'}` : `Gmail Inbox: ${params.query || 'Read / Search'}`,
      category: 'browser',
      icon: <FileText className="w-3.5 h-3.5" />,
      badgeBg: 'bg-red-500/20',
      badgeBorder: 'border-red-500/30',
      badgeText: 'text-red-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool.includes('calendar')) {
    return {
      title: tool.includes('create')
        ? `Google Calendar: Schedule "${params.title || 'Event'}"`
        : `Google Calendar: ${params.query || 'Upcoming Events'}`,
      category: 'system',
      icon: <Clock className="w-3.5 h-3.5" />,
      badgeBg: 'bg-blue-500/20',
      badgeBorder: 'border-blue-500/30',
      badgeText: 'text-blue-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool.includes('google_drive')) {
    return {
      title: tool.includes('upload')
        ? `Google Drive Upload: ${params.title || params.file_path || 'File'}`
        : `Google Drive: ${params.query || params.file_id || 'Search / Read'}`,
      category: 'system',
      icon: <FileText className="w-3.5 h-3.5" />,
      badgeBg: 'bg-emerald-500/20',
      badgeBorder: 'border-emerald-500/30',
      badgeText: 'text-emerald-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool.includes('google_photos')) {
    return {
      title: `Google Photos: ${params.query || 'Memories & Media'}`,
      category: 'vision',
      icon: <Camera className="w-3.5 h-3.5" />,
      badgeBg: 'bg-amber-500/20',
      badgeBorder: 'border-amber-500/30',
      badgeText: 'text-amber-300',
      isPowerShellOrCli: false,
    };
  }

  if (tool.includes('whatsapp') || tool.includes('telegram') || tool.includes('slack') || tool.includes('instagram')) {
    const svc = tool.split('_')[0].toUpperCase();
    const target = params.to || params.channel || params.chat_id || '';
    return {
      title: `${svc}: ${tool.includes('send') ? `Send to ${target || 'Channel'}` : 'Sync / Read'}`,
      category: 'browser',
      icon: <Globe className="w-3.5 h-3.5" />,
      badgeBg: 'bg-cyan-500/20',
      badgeBorder: 'border-cyan-500/30',
      badgeText: 'text-cyan-300',
      isPowerShellOrCli: false,
    };
  }

  // 1. YouTube & Media Playback
  if (
    tool.includes('youtube') ||
    tool === 'play_youtube_video' ||
    tool === 'search_youtube_and_play' ||
    cmdLower.includes('youtube.com') ||
    cmdLower.includes('search_query=')
  ) {
    const q = params.query || params.video_title || extractQuery(rawCmd) || 'YouTube Video';
    const isFull = params.fullscreen || cmdLower.includes('full') || cmdLower.includes('f11');
    return {
      title: `Play YouTube: "${q}"${isFull ? ' in Full Screen' : ''}`,
      category: 'media',
      icon: <Play className="w-3.5 h-3.5 fill-current" />,
      badgeBg: 'bg-red-500/20',
      badgeBorder: 'border-red-500/30',
      badgeText: 'text-red-400',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 2. Full-Screen & Keyboard Shortcuts
  if (
    (tool.includes('computer') && params.action === 'key') ||
    cmdLower.includes('f11') ||
    cmdLower.includes('0x7a') ||
    cmdLower.includes('sendwait(\'{f11}\')') ||
    cmdLower.includes('press(\'f11\')')
  ) {
    const keys = (params.keys || 'F11').toUpperCase();
    const isF11 = keys === 'F11' || cmdLower.includes('f11') || cmdLower.includes('0x7a');
    return {
      title: isF11 ? 'Toggle Full Screen (F11)' : `Send Keystroke: ${keys}`,
      category: 'keyboard',
      icon: isF11 ? <Maximize2 className="w-3.5 h-3.5" /> : <Keyboard className="w-3.5 h-3.5" />,
      badgeBg: 'bg-indigo-500/20',
      badgeBorder: 'border-indigo-500/30',
      badgeText: 'text-indigo-300',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 3. Screen Vision & Screenshots
  if (
    tool === 'capture_screen' ||
    (tool.includes('computer') && params.action === 'capture') ||
    cmdLower.includes('screenshot') ||
    cmdLower.includes('desktop_view') ||
    cmdLower.includes('imagegrab')
  ) {
    return {
      title: 'Captured Desktop Screen View',
      category: 'vision',
      icon: <Camera className="w-3.5 h-3.5" />,
      badgeBg: 'bg-emerald-500/20',
      badgeBorder: 'border-emerald-500/30',
      badgeText: 'text-emerald-300',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 4. Window Focusing & Discovery
  if (
    tool === 'list_open_windows' ||
    (tool.includes('computer') && params.action === 'list_windows') ||
    cmdLower.includes('findwindow') ||
    cmdLower.includes('setforegroundwindow') ||
    cmdLower.includes('enumwindows') ||
    cmdLower.includes('getwindowswithtitle')
  ) {
    let target = 'active windows';
    if (cmdLower.includes('chrome')) target = 'Google Chrome';
    else if (cmdLower.includes('edge')) target = 'Microsoft Edge';
    else if (cmdLower.includes('youtube')) target = 'YouTube Tab';
    else if (cmdLower.includes('valorant')) target = 'Valorant';

    return {
      title: cmdLower.includes('enumwindows') || tool.includes('list')
        ? 'Enumerate Open Desktop Windows'
        : `Bring ${target} to Foreground Focus`,
      category: 'window',
      icon: <AppWindow className="w-3.5 h-3.5" />,
      badgeBg: 'bg-purple-500/20',
      badgeBorder: 'border-purple-500/30',
      badgeText: 'text-purple-300',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 5. Browser Navigation & URLs
  if (
    tool === 'open_browser' ||
    tool === 'open_url' ||
    cmdLower.includes('start chrome') ||
    cmdLower.includes('start msedge') ||
    cmdLower.includes('chrome.exe') ||
    cmdLower.includes('msedge.exe')
  ) {
    let url = params.url || '';
    if (!url) {
      const urlMatch = rawCmd.match(/https?:\/\/[^\s"']+/);
      if (urlMatch) url = urlMatch[0];
    }
    let domain = 'Web Browser';
    if (url) {
      try {
        domain = new URL(url).hostname.replace('www.', '');
      } catch {
        domain = url.slice(0, 30);
      }
    }
    return {
      title: `Open Browser: ${domain}`,
      category: 'browser',
      icon: <Globe className="w-3.5 h-3.5" />,
      badgeBg: 'bg-sky-500/20',
      badgeBorder: 'border-sky-500/30',
      badgeText: 'text-sky-300',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 6. Mouse Clicks & Direct Computer Use
  if (tool.includes('computer') && (params.action === 'click' || params.action === 'double_click' || params.action === 'right_click')) {
    const coords = params.coordinate ? `[${params.coordinate.join(', ')}]` : '';
    const elem = params.element ? `#${params.element}` : '';
    return {
      title: `Mouse ${params.action.replace('_', ' ')} ${coords || elem || 'target'}`,
      category: 'mouse',
      icon: <MousePointer className="w-3.5 h-3.5" />,
      badgeBg: 'bg-blue-500/20',
      badgeBorder: 'border-blue-500/30',
      badgeText: 'text-blue-300',
      isPowerShellOrCli: false,
    };
  }

  // 7. Game Launch & Matchmaking
  if (tool === 'launch_and_play_game' || cmdLower.includes('valorant') || cmdLower.includes('riot client')) {
    const game = params.game_name || 'Game';
    const mode = params.mode ? `(${params.mode})` : '';
    return {
      title: `Queue & Launch: ${game} ${mode}`,
      category: 'game',
      icon: <Gamepad2 className="w-3.5 h-3.5" />,
      badgeBg: 'bg-rose-500/20',
      badgeBorder: 'border-rose-500/30',
      badgeText: 'text-rose-400',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 8. Desktop App Launch
  if (tool === 'launch_app' || tool === 'list_apps') {
    return {
      title: tool === 'list_apps' ? 'Scan Installed Applications' : `Launch Desktop App: ${params.app || 'Application'}`,
      category: 'window',
      icon: <Sparkles className="w-3.5 h-3.5" />,
      badgeBg: 'bg-amber-500/20',
      badgeBorder: 'border-amber-500/30',
      badgeText: 'text-amber-300',
      isPowerShellOrCli: false,
    };
  }

  // 9. Web Search & Research
  if (tool === 'web_search' || tool === 'scrape_url' || tool === 'search_academic_papers') {
    const q = params.query || params.topic || params.url || 'Web Query';
    return {
      title: `Web Intelligence: "${q.length > 30 ? q.slice(0, 30) + '...' : q}"`,
      category: 'search',
      icon: <Search className="w-3.5 h-3.5" />,
      badgeBg: 'bg-cyan-500/20',
      badgeBorder: 'border-cyan-500/30',
      badgeText: 'text-cyan-300',
      isPowerShellOrCli: false,
    };
  }

  // 10. Long-Term Memory
  if (tool.includes('memory')) {
    return {
      title: tool === 'memory_write' ? 'Persist to Long-Term Memory' : 'Semantic Memory Recall',
      category: 'memory',
      icon: <Bookmark className="w-3.5 h-3.5" />,
      badgeBg: 'bg-fuchsia-500/20',
      badgeBorder: 'border-fuchsia-500/30',
      badgeText: 'text-fuchsia-300',
      isPowerShellOrCli: false,
    };
  }

  // 11. System Info & Date/Time
  if (tool.includes('datetime') || tool.includes('system_info') || cmdLower.includes('get-ciminstance') || cmdLower.includes('nvidia-smi')) {
    return {
      title: tool.includes('datetime') ? 'Query Workstation Chronology' : 'Query Hardware & GPU Status',
      category: 'system',
      icon: tool.includes('datetime') ? <Clock className="w-3.5 h-3.5" /> : <Cpu className="w-3.5 h-3.5" />,
      badgeBg: 'bg-teal-500/20',
      badgeBorder: 'border-teal-500/30',
      badgeText: 'text-teal-300',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 12. Process Termination
  if (tool === 'kill_process' || cmdLower.includes('taskkill') || cmdLower.includes('stop-process')) {
    return {
      title: `Terminate Process (PID: ${params.pid || 'Target'})`,
      category: 'process',
      icon: <SquareX className="w-3.5 h-3.5" />,
      badgeBg: 'bg-rose-500/20',
      badgeBorder: 'border-rose-500/30',
      badgeText: 'text-rose-400',
      isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    };
  }

  // 13. File Operations
  if (tool.includes('file') || tool.includes('directory')) {
    const act = tool.replace('_file', '').replace('_directory', '');
    const path = params.path || params.file_path || '';
    return {
      title: `${act.toUpperCase()}: ${path ? path.split(/[/\\]/).pop() : 'Workspace Asset'}`,
      category: 'terminal',
      icon: <FileText className="w-3.5 h-3.5" />,
      badgeBg: 'bg-slate-500/20',
      badgeBorder: 'border-slate-500/30',
      badgeText: 'text-slate-300',
      isPowerShellOrCli: false,
    };
  }

  // 14. Generic CLI / Shell Commands (Clean summary instead of full script)
  let cleanCmd = rawCmd.trim();
  // Strip powershell/cmd prefixes
  cleanCmd = cleanCmd
    .replace(/^powershell\s+-Command\s+["']?/i, '')
    .replace(/^cmd\s+\/c\s+["']?/i, '')
    .replace(/["']?$/, '');
  
  if (cleanCmd.length > 45) {
    cleanCmd = cleanCmd.slice(0, 42) + '...';
  }

  return {
    title: cleanCmd ? `Execute: ${cleanCmd}` : toolCall.tool || 'System Action',
    category: 'terminal',
    icon: <Terminal className="w-3.5 h-3.5" />,
    badgeBg: 'bg-slate-500/20',
    badgeBorder: 'border-slate-500/30',
    badgeText: 'text-slate-300',
    isPowerShellOrCli: tool.includes('command') || rawCmd.length > 0,
    cleanCommandSummary: cleanCmd,
  };
}
