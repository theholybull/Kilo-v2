import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sensor_provider.dart';
import '../providers/audio_provider.dart';
import '../providers/camera_provider.dart';
import '../providers/viam_provider.dart';
import '../providers/pi_connection_provider.dart';
import '../providers/emotion_display_provider.dart';
import '../providers/face_detection_provider.dart';
import '../widgets/sensor_card.dart';
import '../widgets/audio_controls.dart';
import '../widgets/camera_preview.dart';
import '../widgets/viam_connection.dart';
import '../widgets/device_info_card.dart';
import '../widgets/pi_connection_widget.dart';
import '../widgets/emotion_display.dart';
import '../widgets/face_detection_controls.dart';
import 'network_config_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    _initializeProviders();
  }

  Future<void> _initializeProviders() async {
    // Initialize all providers
    await Provider.of<SensorProvider>(context, listen: false).initialize();
    await Provider.of<AudioProvider>(context, listen: false).initialize();
    await Provider.of<CameraProvider>(context, listen: false).initialize();
    await Provider.of<PiConnectionProvider>(context, listen: false).initialize();
    await Provider.of<EmotionDisplayProvider>(context, listen: false).initialize();
    await Provider.of<FaceDetectionProvider>(context, listen: false).initialize();
    
    // Start sensor monitoring
    Provider.of<SensorProvider>(context, listen: false).startMonitoring();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Viam Pi Integration'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          Consumer<PiConnectionProvider>(
            builder: (context, piProvider, child) {
              return IconButton(
                icon: Icon(
                  piProvider.connectionStatus.isConnected 
                    ? Icons.usb 
                    : Icons.usb_off,
                  color: piProvider.connectionStatus.isConnected 
                    ? Colors.green 
                    : Colors.red,
                ),
                onPressed: () => _showPiConnectionDialog(context),
              );
            },
          ),
          Consumer<ViamProvider>(
            builder: (context, viamProvider, child) {
              return IconButton(
                icon: Icon(
                  viamProvider.isConnected 
                    ? Icons.cloud_done 
                    : Icons.cloud_off,
                  color: viamProvider.isConnected 
                    ? Colors.blue 
                    : Colors.grey,
                ),
                onPressed: () => _showViamConnectionDialog(context),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_ethernet),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => const NetworkConfigScreen(),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Pi Connection Status
            const PiConnectionWidget(),
            
            const SizedBox(height: 16),
            
            // Device Info Card
            const DeviceInfoCard(),
            
            const SizedBox(height: 16),
            
            // Emotion Display
            const EmotionDisplay(),
            
            const SizedBox(height: 16),
            
            // Face Detection Controls
            const FaceDetectionControls(),
            
            const SizedBox(height: 16),
            
            // Viam Connection Status (now for local Pi connection)
            Consumer<ViamProvider>(
              builder: (context, viamProvider, child) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              viamProvider.isConnected ? Icons.cloud_done : Icons.cloud_off,
                              color: viamProvider.isConnected ? Colors.green : Colors.red,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Viam Connection',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          viamProvider.isConnected 
                            ? 'Connected to ${viamProvider.robotAddress}'
                            : 'Not connected',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        if (viamProvider.connectionStatus.error != null)
                          Text(
                            'Error: ${viamProvider.connectionStatus.error}',
                            style: const TextStyle(color: Colors.red),
                          ),
                        if (viamProvider.isConnected)
                          ElevatedButton.icon(
                            onPressed: () => _showViamConnectionDialog(context),
                            icon: const Icon(Icons.settings),
                            label: const Text('Settings'),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
            
            const SizedBox(height: 16),
            
            // Sensor Cards
            const SensorCard(),
            
            const SizedBox(height: 16),
            
            // Audio Controls
            const AudioControls(),
            
            const SizedBox(height: 16),
            
            // Camera Preview
            const CameraPreview(),
            
            const SizedBox(height: 16),
            
            // Additional Controls
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Robot Controls',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _testAllSensors(),
                            icon: const Icon(Icons.sensors),
                            label: const Text('Test Sensors'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _testAudio(),
                            icon: const Icon(Icons.mic),
                            label: const Text('Test Audio'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _testCamera(),
                            icon: const Icon(Icons.camera_alt),
                            label: const Text('Test Camera'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _showLogs(context),
                            icon: const Icon(Icons.list_alt),
                            label: const Text('Show Logs'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showPiConnectionDialog(context),
        child: const Icon(Icons.settings),
      ),
    );
  }

  void _showPiConnectionDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Pi Connection Settings'),
        content: const Text('Use the Pi Connection widget to manage USB connection to the Raspberry Pi.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showViamConnectionDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => const ViamConnectionDialog(),
    );
  }

  Future<void> _testAllSensors() async {
    final sensorProvider = Provider.of<SensorProvider>(context, listen: false);
    // Test sensors by checking if data is available
    final accelerometerData = sensorProvider.accelerometerData;
    final gyroscopeData = sensorProvider.gyroscopeData;
    final magnetometerData = sensorProvider.magnetometerData;
    
    if (mounted) {
      String message = 'Sensor test completed - ';
      message += accelerometerData != null ? 'ACC OK ' : 'ACC NO ';
      message += gyroscopeData != null ? 'GYR OK ' : 'GYR NO ';
      message += magnetometerData != null ? 'MAG OK' : 'MAG NO';
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    }
  }

  Future<void> _testAudio() async {
    final audioProvider = Provider.of<AudioProvider>(context, listen: false);
    // Test audio by checking recording state
    final isRecording = audioProvider.isRecording;
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Audio test completed - Recording: $isRecording')),
      );
    }
  }

  Future<void> _testCamera() async {
    final cameraProvider = Provider.of<CameraProvider>(context, listen: false);
    // Test camera by checking if cameras are available
    await cameraProvider.testCameras();
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Camera test completed')),
      );
    }
  }

  void _showLogs(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Application Logs'),
        content: const Text('Log viewer would be implemented here.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}