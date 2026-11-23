import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'scanner_read.dart';
import 'auth_gate.dart';
import 'barcode_camera_page.dart';
import 'auth_api.dart';
import 'scanner_link.dart';
import 'scanner_pairing_page.dart';

const pharmacyPurple = Color(0xFF702583);
const pharmacyGreen = Color(0xFF437D36);

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Farmacia Quilicura',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: pharmacyGreen,
          primary: pharmacyGreen,
          secondary: pharmacyPurple,
          surface: Colors.white,
        ),
        scaffoldBackgroundColor: const Color(0xFFF5F7F6),
        appBarTheme: const AppBarTheme(
          systemOverlayStyle: SystemUiOverlayStyle.dark,
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          foregroundColor: Color(0xFF26332D),
          centerTitle: true,
          elevation: 0,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFFF8FAF9),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 17,
          ),
          prefixIconColor: const Color(0xFF748078),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFDDE4DF)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: pharmacyGreen, width: 1.5),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: pharmacyGreen,
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(52),
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: pharmacyPurple,
            minimumSize: const Size.fromHeight(48),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            side: const BorderSide(color: Color(0xFFDFD7E4)),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      ),
      home: AuthGate(scannerBuilder: (context, api) => ScannerPage(api: api)),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key, required this.api});

  final AuthApi api;

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  ScannerLink? _link;
  bool _connectionBusy = false;
  String? _lastCode;
  ScannerReadRequest? _pendingRead;
  String _lastReadLabel = 'Todavía no hay lecturas';

  bool get _linked => _link?.isLinked ?? false;

  void _showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _toggleConnection() async {
    if (_pendingRead != null) {
      _showMessage(
        'Hay una lectura pendiente. Abre la cámara y reintenta el envío.',
      );
      return;
    }
    if (_connectionBusy) return;

    setState(() {
      _connectionBusy = true;
    });

    try {
      final current = _link;

      if (current != null) {
        final result = await widget.api.revokeScanner(current.id);

        if (!mounted) return;

        if (result.state != 'REVOKED') {
          _showMessage('El servidor no confirmó la desvinculación.');
          return;
        }

        setState(() {
          _link = null;
          _lastCode = null;
        });

        _showMessage('Escáner desvinculado del POS.');
        return;
      }

      final result = await Navigator.of(context).push<ScannerLink>(
        MaterialPageRoute<ScannerLink>(
          builder: (_) => ScannerPairingPage(api: widget.api),
        ),
      );

      if (!mounted || result == null) return;

      if (!result.isLinked) {
        _showMessage('La vinculación no quedó activa.');
        return;
      }

      setState(() {
        _link = result;
        _lastCode = null;
      });

      _showMessage('Escáner vinculado al POS.');
    } on AuthApiException catch (error) {
      _showMessage(error.message);
    } catch (_) {
      _showMessage(
        'No pudimos confirmar la operación. Revisa la conexión y el POS.',
      );
    } finally {
      if (mounted) {
        setState(() {
          _connectionBusy = false;
        });
      }
    }
  }

  Future<bool> _checkConnection() async {
    final current = _link;
    if (current == null || _connectionBusy) return false;

    setState(() {
      _connectionBusy = true;
    });

    try {
      final result = await widget.api.scannerStatus(current.id);

      if (!mounted) return false;

      if (!result.isLinked) {
        setState(() {
          _link = null;
          _lastCode = null;
        });

        _showMessage('La vinculación terminó. Genera un nuevo QR en el POS.');
        return false;
      }

      setState(() {
        _link = result;
      });

      return true;
    } on AuthApiException catch (error) {
      _showMessage(error.message);
      return false;
    } catch (_) {
      _showMessage('No pudimos verificar la conexión con el POS.');
      return false;
    } finally {
      if (mounted) {
        setState(() {
          _connectionBusy = false;
        });
      }
    }
  }

  void _recordRead(ScannerRead read) {
    if (!mounted) return;

    setState(() {
      _lastCode = read.code;
      _lastReadLabel = switch (read.result) {
        'FOUND' => 'Último código recibido por el servidor',
        'NOT_FOUND' => 'Última lectura: producto no encontrado',
        'INACTIVE' => 'Última lectura: producto desactivado',
        _ => 'Última lectura',
      };
    });
  }

  Future<void> _openReader({String? initialCode}) async {
    final linkId = _pendingRead?.linkId ?? _link?.id;
    if (!mounted || linkId == null) return;

    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => BarcodeCameraPage(
          api: widget.api,
          linkId: linkId,
          pendingRead: _pendingRead,
          initialCode: initialCode,
          onSent: _recordRead,
          onPendingChanged: (request) {
            if (!mounted) return;
            setState(() {
              _pendingRead = request;
            });
          },
        ),
      ),
    );
  }

  Future<void> _openCamera() async {
    if (_pendingRead == null) {
      if (!await _checkConnection() || !mounted) return;
    }

    await _openReader();
  }

  Future<void> _manualEntry() async {
    if (_pendingRead != null) {
      await _openCamera();
      return;
    }

    if (!await _checkConnection() || !mounted) return;

    final formKey = GlobalKey<FormState>();
    var enteredCode = '';

    final code = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        void submit() {
          if (formKey.currentState?.validate() ?? false) {
            Navigator.of(dialogContext).pop(enteredCode.trim());
          }
        }

        return AlertDialog(
          title: const Text('Ingresar código'),
          content: Form(
            key: formKey,
            child: TextFormField(
              autofocus: true,
              autocorrect: false,
              enableSuggestions: false,
              maxLength: 128,
              textInputAction: TextInputAction.done,
              decoration: const InputDecoration(labelText: 'Código de barras'),
              onChanged: (value) => enteredCode = value,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Ingresa un código.';
                }
                return null;
              },
              onFieldSubmitted: (_) => submit(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(minimumSize: const Size(100, 48)),
              onPressed: submit,
              child: const Text('Enviar'),
            ),
          ],
        );
      },
    );

    if (!mounted || code == null) return;
    await _openReader(initialCode: code);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escáner de productos')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Center(
                  child: Image.asset(
                    'assets/logo-farmacia.png',
                    width: 220,
                    height: 88,
                    fit: BoxFit.contain,
                    semanticLabel: 'Farmacia Quilicura',
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Venta en caja',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Vincula este dispositivo y envía productos al POS.',
                  style: TextStyle(color: Color(0xFF526159), height: 1.5),
                ),
                const SizedBox(height: 20),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _linked ? Icons.link : Icons.link_off,
                              color: pharmacyGreen,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                _linked ? 'POS vinculado' : 'Vincula una caja',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _linked
                              ? 'Ya puedes escanear productos para esta caja.'
                              : 'Abre Vincular sesión en el POS del computador y escanea su QR.',
                          style: const TextStyle(
                            height: 1.5,
                            color: Color(0xFF526159),
                          ),
                        ),
                        const SizedBox(height: 14),
                        OutlinedButton.icon(
                          onPressed: _connectionBusy ? null : _toggleConnection,
                          icon: Icon(_linked ? Icons.link_off : Icons.qr_code),
                          label: Text(
                            _connectionBusy
                                ? 'Espera…'
                                : _linked
                                ? 'Desvincular'
                                : 'Vincular con el POS',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Center(
                          child: CircleAvatar(
                            radius: 36,
                            backgroundColor: Color(0xFFF3EDF6),
                            child: Icon(
                              Icons.qr_code_scanner_rounded,
                              size: 36,
                              color: pharmacyPurple,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Escanea un producto',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _linked ? 'Enfoca el código de barras del envase.' : 'Primero vincula una caja para activar el lector.',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            height: 1.5,
                            color: Color(0xFF526159),
                          ),
                        ),
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: _linked && !_connectionBusy
                              ? _openCamera
                              : null,
                          icon: const Icon(Icons.camera_alt_outlined),
                          label: const Text('Abrir cámara'),
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: _linked && !_connectionBusy
                              ? _manualEntry
                              : null,
                          icon: const Icon(Icons.keyboard_outlined),
                          label: const Text(
                            'Ingresar código manualmente',
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEAF3E7),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _lastCode == null
                            ? Icons.history
                            : Icons.check_circle_outline,
                        color: pharmacyGreen,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _lastCode == null
                                  ? 'Todavía no hay lecturas'
                                  : _lastReadLabel,
                              style: const TextStyle(color: pharmacyGreen),
                            ),
                            if (_lastCode != null)
                              Text(
                                _lastCode!,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 18,
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
