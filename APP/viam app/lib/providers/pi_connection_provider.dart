import 'package:flutter/foundation.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';
import 'dart:io';

class PiConnectionStatus {
  final bool isConnected;
  final String? piAddress;
  final String? connectionType;
  final String? error;
  final int lastPing;

  PiConnectionStatus({
    required this.isConnected,
    this.piAddress,
    this.connectionType,
    this.error,
    required this.lastPing,
  });
}

class PiConnectionProvider extends ChangeNotifier {
  final Logger _logger = Logger();
  
  PiConnectionStatus _connectionStatus = 
      PiConnectionStatus(isConnected: false, lastPing: -1);
  
  String _piAddress = '10.10.10.1'; // Default Pi address on USB network
  bool _autoConnect = true;
  bool _isScanning = false;
  Timer? _pingTimer;
  Timer? _scanTimer;
  
  // USB networking configuration
  static const String _usbInterface = 'rndis0'; // USB Ethernet interface
  static const int _pingInterval = 5; // seconds
  static const int _scanInterval = 30; // seconds
  
  // Getters
  PiConnectionStatus get connectionStatus => _connectionStatus;
  String get piAddress => _piAddress;
  bool get autoConnect => _autoConnect;
  bool get isScanning => _isScanning;
  
  Future<void> initialize() async {
    _logger.i('Initializing Pi connection provider...');
    
    // Load saved configuration
    await _loadConfiguration();
    
    // Start background monitoring
    _startMonitoring();
    
    // Try to establish initial connection
    if (_autoConnect) {
      await scanForPi();
    }
  }
  
  Future<void> scanForPi() async {
    if (_isScanning) return;
    
    _isScanning = true;
    notifyListeners();
    
    _logger.i('Scanning for Pi on USB network...');
    
    try {
      // Check USB network interface
      final usbInterfaceExists = await _checkUsbInterface();
      if (!usbInterfaceExists) {
        _logger.w('USB network interface not found');
        await _setupUsbNetworking();
      }
      
      // USB tethering addresses only (no WiFi fallback)
      final possibleAddresses = [
        '10.10.10.67', // Pi USB tethering IP
        '10.10.10.1', // Alternative USB tethering
      ];
      
      for (final address in possibleAddresses) {
        if (await _pingPi(address)) {
          _piAddress = address;
          _updateConnectionStatus(
            isConnected: true,
            piAddress: address,
            connectionType: 'USB Ethernet',
            lastPing: await _getPingTime(address),
          );
          
          _logger.i('Found Pi at $address');
          break;
        }
      }
      
      if (!_connectionStatus.isConnected) {
        _updateConnectionStatus(
          isConnected: false,
          error: 'Pi not found on USB network',
          lastPing: -1,
        );
      }
    } catch (e) {
      _logger.e('Error scanning for Pi: $e');
      _updateConnectionStatus(
        isConnected: false,
        error: e.toString(),
        lastPing: -1,
      );
    } finally {
      _isScanning = false;
      notifyListeners();
    }
  }
  
  Future<bool> _checkUsbInterface() async {
    try {
      // Check if USB network interface exists
      final result = await Process.run('ip', ['link', 'show', _usbInterface]);
      return result.exitCode == 0;
    } catch (e) {
      _logger.e('Error checking USB interface: $e');
      return false;
    }
  }
  
  Future<void> _setupUsbNetworking() async {
    try {
      _logger.i('Setting up USB networking...');
      
      // Enable USB tethering (requires root or system permissions)
      // This is a simplified approach - in production you'd need proper system integration
      final result = await Process.run('svc', ['wifi', 'enable']);
      if (result.exitCode != 0) {
        _logger.w('Could not enable USB tethering: ${result.stderr}');
      }
      
      // Wait for interface to come up
      await Future.delayed(const Duration(seconds: 3));
    } catch (e) {
      _logger.e('Error setting up USB networking: $e');
    }
  }
  
  Future<bool> _pingPi(String address) async {
    try {
      final result = await Process.run('ping', ['-c', '1', '-W', '2', address]);
      return result.exitCode == 0;
    } catch (e) {
      _logger.e('Error pinging $address: $e');
      return false;
    }
  }
  
  Future<int> _getPingTime(String address) async {
    try {
      final result = await Process.run('ping', ['-c', '1', address]);
      if (result.exitCode == 0) {
        // Parse ping time from output
        final output = result.stdout as String;
        final timeMatch = RegExp(r'time=(\d+\.?\d*)\s*ms').firstMatch(output);
        if (timeMatch != null) {
          return (double.parse(timeMatch.group(1)!)).round();
        }
      }
      return -1;
    } catch (e) {
      _logger.e('Error getting ping time: $e');
      return -1;
    }
  }
  
  void _startMonitoring() {
    // Ping timer for connection monitoring
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(
      Duration(seconds: _pingInterval), 
      (_) => _checkConnection(),
    );
    
    // Scan timer for periodic rediscovery
    _scanTimer?.cancel();
    _scanTimer = Timer.periodic(
      Duration(seconds: _scanInterval),
      (_) {
        if (!_connectionStatus.isConnected && _autoConnect) {
          scanForPi();
        }
      },
    );
  }
  
  Future<void> _checkConnection() async {
    if (!_connectionStatus.isConnected) return;
    
    final pingTime = await _getPingTime(_piAddress);
    if (pingTime > 0) {
      _updateConnectionStatus(
        isConnected: true,
        piAddress: _piAddress,
        connectionType: 'USB Ethernet',
        lastPing: pingTime,
      );
    } else {
      _logger.w('Lost connection to Pi');
      _updateConnectionStatus(
        isConnected: false,
        error: 'Connection lost',
        lastPing: -1,
      );
    }
  }
  
  Future<bool> connectToPi(String address) async {
    _logger.i('Attempting to connect to Pi at $address');
    
    if (await _pingPi(address)) {
      _piAddress = address;
      _updateConnectionStatus(
        isConnected: true,
        piAddress: address,
        connectionType: 'USB Ethernet',
        lastPing: await _getPingTime(address),
      );
      return true;
    } else {
      _updateConnectionStatus(
        isConnected: false,
        error: 'Cannot reach Pi at $address',
        lastPing: -1,
      );
      return false;
    }
  }
  
  void disconnect() {
    _logger.i('Disconnecting from Pi');
    _updateConnectionStatus(
      isConnected: false,
      error: null,
      lastPing: -1,
    );
  }
  
  void setAutoConnect(bool enabled) {
    _autoConnect = enabled;
    if (enabled && !_connectionStatus.isConnected) {
      scanForPi();
    }
    notifyListeners();
  }
  
  void _updateConnectionStatus({
    required bool isConnected,
    String? piAddress,
    String? connectionType,
    String? error,
    required int lastPing,
  }) {
    _connectionStatus = PiConnectionStatus(
      isConnected: isConnected,
      piAddress: piAddress,
      connectionType: connectionType,
      error: error,
      lastPing: lastPing,
    );
    notifyListeners();
  }
  
  Future<Map<String, dynamic>> getNetworkInfo() async {
    try {
      final networkInfo = NetworkInfo();
      final wifiName = await networkInfo.getWifiName();
      final wifiIP = await networkInfo.getWifiIP();
      final wifiBSSID = await networkInfo.getWifiBSSID();
      
      return {
        'wifi_name': wifiName,
        'wifi_ip': wifiIP,
        'wifi_bssid': wifiBSSID,
        'pi_address': _piAddress,
        'usb_interface': _usbInterface,
        'is_connected': _connectionStatus.isConnected,
        'connection_type': _connectionStatus.connectionType,
        'ping_ms': _connectionStatus.lastPing,
      };
    } catch (e) {
      _logger.e('Error getting network info: $e');
      return {'error': e.toString()};
    }
  }
  
  Future<bool> testViamConnection() async {
    if (!_connectionStatus.isConnected) return false;
    
    try {
      // Test connection to Viam agent on Pi (port 8080)
      final socket = await Socket.connect(_piAddress, 8080, 
          timeout: const Duration(seconds: 5));
      socket.destroy();
      
      _logger.i('Successfully connected to Viam agent on Pi');
      return true;
    } catch (e) {
      _logger.e('Cannot connect to Viam agent: $e');
      return false;
    }
  }
  
  Future<void> _loadConfiguration() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _piAddress = prefs.getString('pi_ip_address') ?? '10.10.10.67';
      _autoConnect = prefs.getBool('auto_connect') ?? true;
      _logger.i('Loaded configuration: Pi IP: $_piAddress, Auto-connect: $_autoConnect');
    } catch (e) {
      _logger.e('Error loading configuration: $e');
      // Use defaults if loading fails
      _piAddress = '10.10.10.67';
      _autoConnect = true;
    }
  }

  Future<void> saveConfiguration(String piAddress, bool autoConnect) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('pi_ip_address', piAddress);
      await prefs.setBool('auto_connect', autoConnect);

      _piAddress = piAddress;
      _autoConnect = autoConnect;

      _logger.i('Saved configuration: Pi IP: $piAddress, Auto-connect: $autoConnect');
      notifyListeners();
    } catch (e) {
      _logger.e('Error saving configuration: $e');
    }
  }

  @override
  void dispose() {
    _pingTimer?.cancel();
    _scanTimer?.cancel();
    super.dispose();
  }
}
