import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/pi_connection_provider.dart';

class NetworkConfigScreen extends StatefulWidget {
  const NetworkConfigScreen({super.key});

  @override
  State<NetworkConfigScreen> createState() => _NetworkConfigScreenState();
}

class _NetworkConfigScreenState extends State<NetworkConfigScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _piIpController;
  late TextEditingController _phoneIpController;
  late TextEditingController _viamPortController;
  
  bool _isLoading = false;
  bool _autoConnect = true;

  @override
  void initState() {
    super.initState();
    _loadSavedConfiguration();
  }

  Future<void> _loadSavedConfiguration() async {
    final prefs = await SharedPreferences.getInstance();
    final piIp = prefs.getString('pi_ip_address') ?? '10.10.10.67';
    final phoneIp = prefs.getString('phone_ip_address') ?? '10.10.10.1';
    final viamPort = prefs.getString('viam_port') ?? '8080';
    final autoConnect = prefs.getBool('auto_connect') ?? true;

    setState(() {
      _piIpController = TextEditingController(text: piIp);
      _phoneIpController = TextEditingController(text: phoneIp);
      _viamPortController = TextEditingController(text: viamPort);
      _autoConnect = autoConnect;
    });
  }

  Future<void> _saveConfiguration() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('pi_ip_address', _piIpController.text.trim());
      await prefs.setString('phone_ip_address', _phoneIpController.text.trim());
      await prefs.setString('viam_port', _viamPortController.text.trim());
      await prefs.setBool('auto_connect', _autoConnect);

      // Update the Pi connection provider with new address
      final piProvider = Provider.of<PiConnectionProvider>(context, listen: false);
      await piProvider.connectToPi(_piIpController.text.trim());

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Configuration saved successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save configuration: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _testConnection() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final piProvider = Provider.of<PiConnectionProvider>(context, listen: false);
      final success = await piProvider.connectToPi(_piIpController.text.trim());

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success ? 'Connection successful!' : 'Connection failed'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection test failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Network Configuration'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Connection Status Card
              Consumer<PiConnectionProvider>(
                builder: (context, piProvider, child) {
                  return Card(
                    color: piProvider.connectionStatus.isConnected
                        ? Colors.green.withOpacity(0.1)
                        : Colors.red.withOpacity(0.1),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Row(
                        children: [
                          Icon(
                            piProvider.connectionStatus.isConnected
                                ? Icons.check_circle
                                : Icons.error,
                            color: piProvider.connectionStatus.isConnected
                                ? Colors.green
                                : Colors.red,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  piProvider.connectionStatus.isConnected
                                      ? 'Connected'
                                      : 'Disconnected',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                if (piProvider.connectionStatus.piAddress != null)
                                  Text(
                                    'Pi: ${piProvider.connectionStatus.piAddress}',
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                if (piProvider.connectionStatus.lastPing > 0)
                                  Text(
                                    'Ping: ${piProvider.connectionStatus.lastPing}ms',
                                    style: const TextStyle(fontSize: 12),
                                  ),
                              ],
                            ),
                          ),
                          if (piProvider.isScanning)
                            const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),

              const SizedBox(height: 24),

              // IP Configuration
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      // Pi IP Address
                      TextFormField(
                        controller: _piIpController,
                        decoration: const InputDecoration(
                          labelText: 'Pi IP Address',
                          hintText: 'e.g., 10.10.10.67',
                          prefixIcon: Icon(Icons.router),
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter Pi IP address';
                          }
                          final ipRegex = RegExp(
                            r'^(\d{1,3}\.){3}\d{1,3}$',
                          );
                          if (!ipRegex.hasMatch(value)) {
                            return 'Please enter a valid IP address';
                          }
                          return null;
                        },
                      ),

                      const SizedBox(height: 16),

                      // Phone IP Address
                      TextFormField(
                        controller: _phoneIpController,
                        decoration: const InputDecoration(
                          labelText: 'Phone IP Address',
                          hintText: 'e.g., 10.10.10.1',
                          prefixIcon: Icon(Icons.smartphone),
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter phone IP address';
                          }
                          final ipRegex = RegExp(
                            r'^(\d{1,3}\.){3}\d{1,3}$',
                          );
                          if (!ipRegex.hasMatch(value)) {
                            return 'Please enter a valid IP address';
                          }
                          return null;
                        },
                      ),

                      const SizedBox(height: 16),

                      // Viam Port
                      TextFormField(
                        controller: _viamPortController,
                        decoration: const InputDecoration(
                          labelText: 'Viam Port',
                          hintText: 'e.g., 8080',
                          prefixIcon: Icon(Icons.settings_ethernet),
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter Viam port';
                          }
                          final port = int.tryParse(value);
                          if (port == null || port < 1 || port > 65535) {
                            return 'Please enter a valid port (1-65535)';
                          }
                          return null;
                        },
                      ),

                      const SizedBox(height: 24),

                      // Auto Connect Switch
                      SwitchListTile(
                        title: const Text('Auto-connect on startup'),
                        subtitle: const Text('Automatically try to connect when app starts'),
                        value: _autoConnect,
                        onChanged: (value) {
                          setState(() => _autoConnect = value);
                        },
                      ),

                      const SizedBox(height: 24),

                      // Quick Setup Buttons
                      const Text(
                        'Quick Setup',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),

                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ElevatedButton.icon(
                            onPressed: () {
                              _piIpController.text = '10.10.10.67';
                              _phoneIpController.text = '10.10.10.1';
                              _viamPortController.text = '8080';
                            },
                            icon: const Icon(Icons.usb),
                            label: const Text('USB Tethering'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.blue.withOpacity(0.1),
                            ),
                          ),
                          ElevatedButton.icon(
                            onPressed: () {
                              _piIpController.text = '192.168.1.100';
                              _phoneIpController.text = '192.168.1.50';
                              _viamPortController.text = '8080';
                            },
                            icon: const Icon(Icons.wifi),
                            label: const Text('WiFi Network'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green.withOpacity(0.1),
                            ),
                          ),
                          ElevatedButton.icon(
                            onPressed: () {
                              _piIpController.text = '172.20.10.1';
                              _phoneIpController.text = '172.20.10.2';
                              _viamPortController.text = '8080';
                            },
                            icon: const Icon(Icons.mobile_off),
                            label: const Text('Hotspot'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.orange.withOpacity(0.1),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 32),

                      // Action Buttons
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _isLoading ? null : _testConnection,
                              icon: _isLoading
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.network_check),
                              label: Text(_isLoading ? 'Testing...' : 'Test Connection'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: _isLoading ? null : _saveConfiguration,
                              icon: _isLoading
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.save),
                              label: Text(_isLoading ? 'Saving...' : 'Save Configuration'),
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
      ),
    );
  }

  @override
  void dispose() {
    _piIpController.dispose();
    _phoneIpController.dispose();
    _viamPortController.dispose();
    super.dispose();
  }
}