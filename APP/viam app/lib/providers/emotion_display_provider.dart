import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'dart:async';
import 'dart:math';

enum Emotion {
  happy,
  sad,
  angry,
  surprised,
  neutral,
  curious,
  focused,
  sleepy,
  excited,
  confused,
}

enum EyeState {
  open,
  halfOpen,
  closed,
  blinking,
  looking,
  tracking,
}

class EmotionDisplayProvider extends ChangeNotifier {
  final Logger _logger = Logger();
  
  Emotion _currentEmotion = Emotion.neutral;
  EyeState _eyeState = EyeState.open;
  double _eyeX = 0.0; // -1 to 1 (left to right)
  double _eyeY = 0.0; // -1 to 1 (up to down)
  double _steeringAngle = 0.0; // -45 to 45 degrees
  bool _isTracking = false;
  String? _trackedPersonId;
  Timer? _blinkTimer;
  Timer? _emotionTimer;
  Timer? _trackingTimer;
  
  // Eye animation parameters
  double _blinkProgress = 0.0;
  bool _isBlinking = false;
  double _pupilSize = 0.3;
  double _eyeOpenness = 1.0;
  
  // Emotion transition parameters
  double _emotionIntensity = 0.0;
  Emotion? _targetEmotion;
  
  // Getters
  Emotion get currentEmotion => _currentEmotion;
  EyeState get eyeState => _eyeState;
  double get eyeX => _eyeX;
  double get eyeY => _eyeY;
  double get steeringAngle => _steeringAngle;
  bool get isTracking => _isTracking;
  String? get trackedPersonId => _trackedPersonId;
  double get blinkProgress => _blinkProgress;
  bool get isBlinking => _isBlinking;
  double get pupilSize => _pupilSize;
  double get eyeOpenness => _eyeOpenness;
  double get emotionIntensity => _emotionIntensity;
  
  Future<void> initialize() async {
    _logger.i('Initializing emotion display provider...');
    
    // Start automatic blinking
    _startBlinking();
    
    // Start random eye movements
    _startRandomEyeMovements();
    
    // Set initial neutral emotion
    setEmotion(Emotion.neutral);
  }
  
  void setEmotion(Emotion emotion, {double intensity = 1.0}) {
    _logger.i('Setting emotion to: $emotion with intensity: $intensity');
    
    _targetEmotion = emotion;
    _emotionIntensity = intensity;
    
    // Animate emotion transition
    _animateEmotionTransition();
  }
  
  void _animateEmotionTransition() {
    if (_targetEmotion == null) return;
    
    const transitionDuration = Duration(milliseconds: 500);
    const steps = 20;
    final stepDuration = transitionDuration.inMilliseconds ~/ steps;
    
    double startIntensity = _emotionIntensity;
    
    for (int i = 0; i <= steps; i++) {
      Future.delayed(Duration(milliseconds: i * stepDuration), () {
        final progress = i / steps;
        _emotionIntensity = startIntensity + (1.0 - startIntensity) * progress;
        
        if (i == steps) {
          _currentEmotion = _targetEmotion!;
          _targetEmotion = null;
        }
        
        notifyListeners();
      });
    }
  }
  
  void setEyePosition(double x, double y) {
    _eyeX = x.clamp(-1.0, 1.0);
    _eyeY = y.clamp(-1.0, 1.0);
    
    // Adjust pupil position based on eye position
    _pupilSize = 0.3 + (1.0 - (_eyeX.abs() + _eyeY.abs()) / 2.0) * 0.2;
    
    notifyListeners();
  }
  
  void setSteeringAngle(double angle) {
    _steeringAngle = angle.clamp(-45.0, 45.0);
    
    // Move eyes in direction of steering (both eyes same direction)
    double eyeOffset = angle / 45.0; // Convert to -1 to 1 range
    _eyeX = eyeOffset.clamp(-1.0, 1.0);
    
    // Adjust pupil position based on eye position
    _pupilSize = 0.3 + (1.0 - (_eyeX.abs() + _eyeY.abs()) / 2.0) * 0.2;
    
    notifyListeners();
  }
  
  void startTrackingPerson(String personId) {
    _logger.i('Starting to track person: $personId');
    _isTracking = true;
    _trackedPersonId = personId;
    _eyeState = EyeState.tracking;
    
    // Start tracking animation
    _startTrackingAnimation();
    
    notifyListeners();
  }
  
  void stopTracking() {
    _logger.i('Stopping person tracking');
    _isTracking = false;
    _trackedPersonId = null;
    _eyeState = EyeState.open;
    
    _trackingTimer?.cancel();
    _trackingTimer = null;
    
    // Return eyes to neutral position
    setEyePosition(0.0, 0.0);
    
    notifyListeners();
  }
  
  void _startTrackingAnimation() {
    _trackingTimer?.cancel();
    _trackingTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      if (!_isTracking) return;
      
      // Simulate smooth tracking movement
      // In real implementation, this would follow face position
      final targetX = sin(DateTime.now().millisecondsSinceEpoch / 1000.0) * 0.3;
      final targetY = cos(DateTime.now().millisecondsSinceEpoch / 1500.0) * 0.2;
      
      // Smooth movement
      _eyeX += (targetX - _eyeX) * 0.1;
      _eyeY += (targetY - _eyeY) * 0.1;
      
      notifyListeners();
    });
  }
  
  void _startBlinking() {
    _blinkTimer?.cancel();
    _blinkTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!_isBlinking && _eyeState != EyeState.closed) {
        _blink();
      }
    });
  }
  
  void _blink() {
    _isBlinking = true;
    _blinkProgress = 0.0;
    
    const blinkDuration = Duration(milliseconds: 200);
    const steps = 10;
    final stepDuration = blinkDuration.inMilliseconds ~/ steps;
    
    // Close eyes
    for (int i = 0; i <= steps; i++) {
      Future.delayed(Duration(milliseconds: i * stepDuration), () {
        _blinkProgress = i / steps;
        _eyeOpenness = 1.0 - _blinkProgress;
        notifyListeners();
      });
    }
    
    // Open eyes
    Future.delayed(const Duration(milliseconds: 200), () {
      for (int i = 0; i <= steps; i++) {
        Future.delayed(Duration(milliseconds: i * stepDuration), () {
          _blinkProgress = 1.0 - (i / steps);
          _eyeOpenness = _blinkProgress;
          notifyListeners();
        });
      }
      
      Future.delayed(blinkDuration, () {
        _isBlinking = false;
        _blinkProgress = 0.0;
        _eyeOpenness = 1.0;
        notifyListeners();
      });
    });
  }
  
  void _startRandomEyeMovements() {
    _emotionTimer?.cancel();
    _emotionTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (_isTracking || _isBlinking) return;
      
      // Random saccades
      final random = Random();
      if (random.nextDouble() < 0.3) { // 30% chance of movement
        final newX = (random.nextDouble() - 0.5) * 0.4;
        final newY = (random.nextDouble() - 0.5) * 0.3;
        setEyePosition(newX, newY);
      }
    });
  }
  
  Map<String, dynamic> getEyeParameters() {
    return {
      'emotion': _currentEmotion.toString(),
      'eye_state': _eyeState.toString(),
      'eye_x': _eyeX,
      'eye_y': _eyeY,
      'steering_angle': _steeringAngle,
      'is_tracking': _isTracking,
      'tracked_person_id': _trackedPersonId,
      'blink_progress': _blinkProgress,
      'is_blinking': _isBlinking,
      'pupil_size': _pupilSize,
      'eye_openness': _eyeOpenness,
      'emotion_intensity': _emotionIntensity,
    };
  }
  
  // Emotion-specific eye behaviors
  void updateEmotionBehavior() {
    switch (_currentEmotion) {
      case Emotion.happy:
        _pupilSize = 0.4;
        _eyeY = -0.1; // Slightly up
        break;
      case Emotion.sad:
        _pupilSize = 0.2;
        _eyeY = 0.2; // Looking down
        _eyeOpenness = 0.7; // Slightly droopy
        break;
      case Emotion.angry:
        _pupilSize = 0.1;
        _eyeY = -0.1; // Intense gaze
        break;
      case Emotion.surprised:
        _pupilSize = 0.5;
        _eyeOpenness = 1.2; // Wide eyes
        break;
      case Emotion.curious:
        _pupilSize = 0.35;
        // Head tilt effect simulated by eye asymmetry
        _eyeX = 0.1;
        break;
      case Emotion.focused:
        _pupilSize = 0.25;
        // Reduced movement
        break;
      case Emotion.sleepy:
        _eyeOpenness = 0.3;
        _pupilSize = 0.15;
        break;
      case Emotion.excited:
        _pupilSize = 0.45;
        // Increased random movement
        break;
      case Emotion.confused:
        _eyeX = sin(DateTime.now().millisecondsSinceEpoch / 500.0) * 0.2;
        _pupilSize = 0.3;
        break;
      case Emotion.neutral:
      default:
        _pupilSize = 0.3;
        _eyeOpenness = 1.0;
        break;
    }
    
    notifyListeners();
  }
  
  @override
  void dispose() {
    _blinkTimer?.cancel();
    _emotionTimer?.cancel();
    _trackingTimer?.cancel();
    super.dispose();
  }
}