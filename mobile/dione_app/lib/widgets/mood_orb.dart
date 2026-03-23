import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';

/// The Mood Orb — Dione's visual heartbeat.
///
/// A glowing, breathing orb that reflects Dione's current
/// emotional state. It pulses, shifts color, and changes
/// intensity based on mood dimensions.
class MoodOrb extends StatefulWidget {
  final double size;
  final bool showLabel;

  const MoodOrb({super.key, this.size = 120, this.showLabel = true});

  @override
  State<MoodOrb> createState() => _MoodOrbState();
}

class _MoodOrbState extends State<MoodOrb>
    with TickerProviderStateMixin {
  late AnimationController _breatheController;
  late AnimationController _pulseController;
  late Animation<double> _breatheAnimation;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    // Breathing animation — continuous slow pulse
    _breatheController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    )..repeat(reverse: true);

    _breatheAnimation = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(parent: _breatheController, curve: Curves.easeInOut),
    );

    // Pulse animation — faster, for high-energy moments
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _breatheController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, theme, _) {
        final mood = theme.mood;
        final gradient = theme.moodGradient;
        final glowIntensity = theme.avatarGlowIntensity;

        // Adjust breathing speed based on energy
        _breatheController.duration = Duration(
          milliseconds: (4000 - (mood.energy * 2000)).toInt().clamp(1500, 4000),
        );

        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedBuilder(
              animation: _breatheAnimation,
              builder: (context, child) {
                return AnimatedBuilder(
                  animation: _pulseAnimation,
                  builder: (context, _) {
                    final scale = _breatheAnimation.value;
                    final pulseGlow = _pulseAnimation.value * mood.energy;

                    return Transform.scale(
                      scale: scale,
                      child: Container(
                        width: widget.size,
                        height: widget.size,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              gradient[0].withOpacity(0.9),
                              gradient[1].withOpacity(0.7),
                              gradient[1].withOpacity(0.0),
                            ],
                            stops: const [0.0, 0.6, 1.0],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: gradient[0]
                                  .withOpacity(0.3 + pulseGlow * 0.3),
                              blurRadius: glowIntensity + pulseGlow * 20,
                              spreadRadius: 5 + pulseGlow * 10,
                            ),
                            BoxShadow(
                              color: gradient[1]
                                  .withOpacity(0.2 + pulseGlow * 0.2),
                              blurRadius: glowIntensity * 1.5,
                              spreadRadius: 2,
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            mood.moodEmoji,
                            style: TextStyle(fontSize: widget.size * 0.35),
                          ),
                        ),
                      ),
                    );
                  },
                );
              },
            ),
            if (widget.showLabel) ...[
              const SizedBox(height: 16),
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 500),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: gradient[0].withOpacity(0.8),
                  letterSpacing: 2,
                ),
                child: Text(mood.label.toUpperCase()),
              ),
            ],
          ],
        );
      },
    );
  }
}
