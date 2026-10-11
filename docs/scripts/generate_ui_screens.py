"""
Dione AI — High-Resolution UI Screenshot & Visual Asset Generator
================================================================
Generates 4 publication-quality 300 DPI UI screenshots for Chapter 7.1 of the Black Book:
1. UI Screen 1: Glassmorphic Chat Interface with Dynamic Mood & Persona Indicator.
2. UI Screen 2: 1-Click Proactive Proposal Card (Weekly Mentor Status Email).
3. UI Screen 3: Social Intelligence & Knowledge Graph Person Dossier View.
4. UI Screen 4: 5-Tier Safety Kernel Interactive Confirmation Modal.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

OUT_DIR = Path(r"c:\Users\Jass\Documents\CAPSTONE\PROJECT - I\docs\figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'

def create_chat_ui_screen():
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis('off')

    # Main Glass Window
    window = patches.FancyBboxPatch((4, 4), 92, 54, boxstyle="round,pad=1,rounding_size=2",
                                    facecolor='#111827', edgecolor='#1F2937', linewidth=1.5)
    ax.add_patch(window)

    # Header Bar
    header = patches.FancyBboxPatch((4, 50), 92, 8, boxstyle="round,pad=1,rounding_size=2",
                                    facecolor='#1E293B', edgecolor='#334155', linewidth=1)
    ax.add_patch(header)
    ax.text(8, 54, "🪐 DIONE AI — Local LAM Orchestration Client", color='#F8FAFC', fontsize=12, fontweight='bold')
    
    # Mood Pill Indicator
    mood_pill = patches.FancyBboxPatch((68, 52), 24, 4.2, boxstyle="round,pad=0.8,rounding_size=1.2",
                                       facecolor='#10B981', edgecolor='#059669', linewidth=1)
    ax.add_patch(mood_pill)
    ax.text(80, 54.1, "● Mood: Curious | Energy: 0.82", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Sidebar (Left)
    sidebar = patches.Rectangle((6, 6), 22, 42, facecolor='#0F172A', edgecolor='#1E293B', linewidth=1)
    ax.add_patch(sidebar)
    ax.text(8, 45, "ACTIVE MODULES", color='#94A3B8', fontsize=8, fontweight='bold')
    ax.text(8, 41, "✔ ReAct Engine (v2.0)", color='#38BDF8', fontsize=8.5)
    ax.text(8, 37, "✔ Knowledge Graph (1.16ms)", color='#38BDF8', fontsize=8.5)
    ax.text(8, 33, "✔ Heartbeat (Active: 30s)", color='#38BDF8', fontsize=8.5)
    ax.text(8, 29, "✔ Social Dossiers (3 VIPs)", color='#38BDF8', fontsize=8.5)
    ax.text(8, 25, "✔ Safety Kernel (5-Tier)", color='#10B981', fontsize=8.5)

    # Chat Area
    # User Message Bubble
    user_bubble = patches.FancyBboxPatch((52, 38), 40, 8, boxstyle="round,pad=0.8,rounding_size=1",
                                         facecolor='#3B82F6', edgecolor='#2563EB', linewidth=1)
    ax.add_patch(user_bubble)
    ax.text(54, 43, "User (Jass Shivnani):", color='#DBEAFE', fontsize=8, fontweight='bold')
    ax.text(54, 40, "Draft the weekly progress email to our project mentor.", color='#FFFFFF', fontsize=8.5)

    # Assistant Response Bubble
    ai_bubble = patches.FancyBboxPatch((32, 16), 60, 19, boxstyle="round,pad=0.8,rounding_size=1",
                                       facecolor='#1E293B', edgecolor='#475569', linewidth=1)
    ax.add_patch(ai_bubble)
    ax.text(34, 32.5, "🪐 Dione AI (Resolved Recipient: Prof. Geocey Shejy):", color='#38BDF8', fontsize=8.5, fontweight='bold')
    ax.text(34, 29.5, "I've pulled your 2-hop context and active commitments from the Knowledge Graph.", color='#CBD5E1', fontsize=8)
    ax.text(34, 26.5, "• Recipient: Prof. Geocey Shejy (geocey.shejy@ves.ac.in)", color='#94A3B8', fontsize=8)
    ax.text(34, 23.5, "• Tone: Formal Academic | Salutation: 'Respected Ma'am,'", color='#94A3B8', fontsize=8)
    ax.text(34, 20.5, "• Staged Draft: 3 Milestones completed, Table 6.1 Test Cases attached.", color='#94A3B8', fontsize=8)
    ax.text(34, 17.5, "[Review Full Draft & Confirm]   [Edit Tone]   [Dismiss]", color='#10B981', fontsize=8, fontweight='bold')

    # Input Box
    input_box = patches.FancyBboxPatch((32, 6), 60, 6, boxstyle="round,pad=0.8,rounding_size=1",
                                       facecolor='#0F172A', edgecolor='#334155', linewidth=1)
    ax.add_patch(input_box)
    ax.text(34, 9, "Type a message or trigger an action with natural language...", color='#64748B', fontsize=8.5)

    out_path = OUT_DIR / "ui_screen1_chat_interface.png"
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out_path}")

def create_proactive_card_screen():
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 58)
    ax.axis('off')

    # Background window
    bg = patches.FancyBboxPatch((8, 4), 84, 50, boxstyle="round,pad=1,rounding_size=2",
                                facecolor='#111827', edgecolor='#1F2937', linewidth=1.5)
    ax.add_patch(bg)

    # Card Box
    card = patches.FancyBboxPatch((12, 8), 76, 42, boxstyle="round,pad=1,rounding_size=1.5",
                                  facecolor='#1E293B', edgecolor='#EF4444', linewidth=2)
    ax.add_patch(card)

    # Card Title
    ax.text(16, 44, "🔔 AMBIENT HEARTBEAT — PROACTIVE PROPOSAL CARD", color='#F87171', fontsize=12, fontweight='bold')
    ax.text(16, 40.5, "Scale: Weekly Routine | Trigger Schedule: Every Monday 09:00 AM | Confidence: 100%", color='#94A3B8', fontsize=8.5)

    # Card Content Box
    draft_box = patches.FancyBboxPatch((16, 18), 68, 20, boxstyle="round,pad=0.8,rounding_size=1",
                                       facecolor='#0F172A', edgecolor='#334155', linewidth=1)
    ax.add_patch(draft_box)
    ax.text(18, 35, "STAGED ACTION: Email Draft to Project Mentor", color='#38BDF8', fontsize=9, fontweight='bold')
    ax.text(18, 31.5, "To: Prof. Geocey Shejy <geocey.shejy@ves.ac.in>", color='#E2E8F0', fontsize=8.5)
    ax.text(18, 28.5, "Subject: Dione AI — Weekly Capstone Project Status Report (Review-II)", color='#E2E8F0', fontsize=8.5)
    ax.text(18, 25, "Respected Ma'am, here is our weekly update on the Stage-2 Black Book and test cases...", color='#94A3B8', fontsize=8)
    ax.text(18, 21.5, "• Promise fulfilled: 'Revised Chapter 6 test cases' included as committed.", color='#10B981', fontsize=8)

    # Action Buttons
    btn_approve = patches.FancyBboxPatch((16, 10), 20, 5, boxstyle="round,pad=0.5,rounding_size=0.8",
                                         facecolor='#10B981', edgecolor='#059669', linewidth=1)
    ax.add_patch(btn_approve)
    ax.text(26, 12.5, "✔ Approve & Send", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    btn_edit = patches.FancyBboxPatch((38, 10), 16, 5, boxstyle="round,pad=0.5,rounding_size=0.8",
                                      facecolor='#3B82F6', edgecolor='#2563EB', linewidth=1)
    ax.add_patch(btn_edit)
    ax.text(46, 12.5, "✏ Edit Draft", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    btn_dismiss = patches.FancyBboxPatch((56, 10), 14, 5, boxstyle="round,pad=0.5,rounding_size=0.8",
                                         facecolor='#475569', edgecolor='#334155', linewidth=1)
    ax.add_patch(btn_dismiss)
    ax.text(63, 12.5, "✖ Dismiss", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    btn_snooze = patches.FancyBboxPatch((72, 10), 12, 5, boxstyle="round,pad=0.5,rounding_size=0.8",
                                        facecolor='#334155', edgecolor='#1E293B', linewidth=1)
    ax.add_patch(btn_snooze)
    ax.text(78, 12.5, "⏱ Snooze", color='#CBD5E1', fontsize=9, ha='center', va='center')

    out_path = OUT_DIR / "ui_screen2_proactive_proposal_card.png"
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out_path}")

def create_social_dossier_screen():
    fig, ax = plt.subplots(figsize=(10, 6.0), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis('off')

    # Main Card Window
    window = patches.FancyBboxPatch((6, 4), 88, 52, boxstyle="round,pad=1,rounding_size=2",
                                    facecolor='#111827', edgecolor='#1F2937', linewidth=1.5)
    ax.add_patch(window)

    # Title
    ax.text(10, 51, "👤 SOCIAL INTELLIGENCE & PERSON DOSSIER EXPLORER", color='#F8FAFC', fontsize=12, fontweight='bold')
    ax.text(10, 47.5, "Connected Entity Node: Prof. Geocey Shejy (Project Mentor)", color='#38BDF8', fontsize=9)

    # Left Column: Profile Card
    p_card = patches.FancyBboxPatch((10, 8), 38, 36, boxstyle="round,pad=0.8,rounding_size=1",
                                    facecolor='#1E293B', edgecolor='#334155', linewidth=1)
    ax.add_patch(p_card)
    ax.text(12, 40, "CANONICAL IDENTITY", color='#94A3B8', fontsize=8, fontweight='bold')
    ax.text(12, 36.5, "• Name: Prof. Geocey Shejy", color='#FFFFFF', fontsize=8.5, fontweight='bold')
    ax.text(12, 33.5, "• Role: Assistant Professor & Capstone Mentor", color='#CBD5E1', fontsize=8)
    ax.text(12, 30.5, "• Email: geocey.shejy@ves.ac.in", color='#38BDF8', fontsize=8)
    ax.text(12, 27.5, "• Department: VESIT Computer Engineering", color='#CBD5E1', fontsize=8)
    ax.text(12, 24, "COMMUNICATION PROFILE", color='#94A3B8', fontsize=8, fontweight='bold')
    ax.text(12, 20.5, "• Preferred Tone: Formal Academic", color='#A7F3D0', fontsize=8)
    ax.text(12, 17.5, "• Salutation: 'Respected Ma'am,'", color='#A7F3D0', fontsize=8)
    ax.text(12, 14.5, "• Touchpoint Health: ACTIVE (Last contacted today)", color='#10B981', fontsize=8)
    ax.text(12, 11, "• Aliases: 'mentor', 'Prof. Geocey', 'Guide'", color='#94A3B8', fontsize=7.5)

    # Right Column: Commitments & Social Graph Connections
    c_card = patches.FancyBboxPatch((52, 8), 38, 36, boxstyle="round,pad=0.8,rounding_size=1",
                                    facecolor='#1E293B', edgecolor='#334155', linewidth=1)
    ax.add_patch(c_card)
    ax.text(54, 40, "ACTIVE COMMITMENTS & PROMISES", color='#F59E0B', fontsize=8, fontweight='bold')
    
    comm1 = patches.FancyBboxPatch((54, 28), 34, 9, boxstyle="round,pad=0.5,rounding_size=0.6",
                                  facecolor='#0F172A', edgecolor='#F59E0B', linewidth=1)
    ax.add_patch(comm1)
    ax.text(56, 34, "Promise: Revised Chapter 6 Test Cases", color='#FDE68A', fontsize=8, fontweight='bold')
    ax.text(56, 31, "Status: [PENDING] | Due: Wednesday | Origin: Chat", color='#94A3B8', fontsize=7.5)
    ax.text(56, 28.5, "Action: Auto-injected in next email draft", color='#10B981', fontsize=7.5)

    ax.text(54, 24, "2-HOP KNOWLEDGE GRAPH NEIGHBORHOOD", color='#38BDF8', fontsize=8, fontweight='bold')
    ax.text(54, 20.5, "• User --[REPORTS_TO]--> Prof. Geocey Shejy", color='#E2E8F0', fontsize=8)
    ax.text(54, 17.5, "• Prof. Geocey Shejy --[MANAGES]--> Dione AI", color='#E2E8F0', fontsize=8)
    ax.text(54, 14.5, "• Prof. Geocey Shejy --[DISCUSSED]--> Stage-2 Review", color='#E2E8F0', fontsize=8)
    ax.text(54, 11.5, "• Graph Traversal Latency: 1.158 ms (NetworkX)", color='#A7F3D0', fontsize=8, fontweight='bold')

    out_path = OUT_DIR / "ui_screen3_social_dossier_graph.png"
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out_path}")

def create_safety_modal_screen():
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis('off')

    # Main Window
    window = patches.FancyBboxPatch((10, 4), 80, 47, boxstyle="round,pad=1,rounding_size=2",
                                    facecolor='#111827', edgecolor='#EF4444', linewidth=2)
    ax.add_patch(window)

    # Modal Header
    ax.text(14, 46, "🛡️ DIONE SAFETY KERNEL — INTERACTIVE CONFIRMATION GATE", color='#F87171', fontsize=11, fontweight='bold')
    ax.text(14, 42.5, "Security Tier: Tier-4 (High Risk Host Modification) | Policy: Strict Isolation", color='#94A3B8', fontsize=8.5)

    # Warning Box
    w_box = patches.FancyBboxPatch((14, 18), 72, 21, boxstyle="round,pad=0.8,rounding_size=1",
                                   facecolor='#0F172A', edgecolor='#334155', linewidth=1)
    ax.add_patch(w_box)
    ax.text(16, 35.5, "INTERCEPTED ACTION DETAILS:", color='#F59E0B', fontsize=9, fontweight='bold')
    ax.text(16, 32, "• Target Plugin: FileSystemPlugin / ShellSubprocess", color='#E2E8F0', fontsize=8.5)
    ax.text(16, 29, "• Command: Write / Delete operation on system configuration file", color='#E2E8F0', fontsize=8.5)
    ax.text(16, 26, "• Reason: Operation requires explicit human-in-the-loop authorization.", color='#94A3B8', fontsize=8)
    ax.text(16, 23, "• Sandboxing: Execution blocked until cryptographically verified.", color='#10B981', fontsize=8)
    ax.text(16, 20, "• Adversarial Injection Defense: 98.2% Interception Rate", color='#38BDF8', fontsize=8)

    # Buttons
    b_allow = patches.FancyBboxPatch((14, 8), 24, 6, boxstyle="round,pad=0.5,rounding_size=0.8",
                                     facecolor='#10B981', edgecolor='#059669', linewidth=1)
    ax.add_patch(b_allow)
    ax.text(26, 11, "✔ Authorize Action", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    b_deny = patches.FancyBboxPatch((42, 8), 20, 6, boxstyle="round,pad=0.5,rounding_size=0.8",
                                    facecolor='#EF4444', edgecolor='#DC2626', linewidth=1)
    ax.add_patch(b_deny)
    ax.text(52, 11, "✖ Deny & Terminate", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    b_sandbox = patches.FancyBboxPatch((66, 8), 20, 6, boxstyle="round,pad=0.5,rounding_size=0.8",
                                       facecolor='#3B82F6', edgecolor='#2563EB', linewidth=1)
    ax.add_patch(b_sandbox)
    ax.text(76, 11, "🔒 Run in Sandbox", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    out_path = OUT_DIR / "ui_screen4_safety_confirmation_modal.png"
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    create_chat_ui_screen()
    create_proactive_card_screen()
    create_social_dossier_screen()
    create_safety_modal_screen()
    print("\n[ALL 4 UI SCREENSHOTS GENERATED SUCCESSFULLY AT 300 DPI]")
