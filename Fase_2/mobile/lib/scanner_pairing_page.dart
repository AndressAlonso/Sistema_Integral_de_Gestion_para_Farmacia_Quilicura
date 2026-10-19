import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'auth_api.dart';
import 'scanner_link.dart';

class ScannerPairingPage extends StatefulWidget {
  const ScannerPairingPage({super.key, required this.api});

  final AuthApi api;

  @override
  State<ScannerPairingPage> createState() => _ScannerPairingPageState();
}

class _ScannerPairingPageState extends State<ScannerPairingPage> {
  bool _busy = false;
  String? _error;

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (!mounted ||
        _busy ||
        _error != null ||
        ModalRoute.of(context)?.isCurrent != true) {
      return;
    }

    final codes = capture.barcodes
        .where((barcode) => barcode.format == BarcodeFormat.qrCode)
        .map((barcode) => barcode.rawValue)
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toSet();

    if (codes.isEmpty) return;

    if (codes.length != 1) {
      setState(() {
        _error = 'Enfoca solamente el QR de la caja que quieres vincular.';
      });
      return;
    }

    // Bloquea nuevas lecturas antes de iniciar la petición.
    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final link = await widget.api.claimScanner(codes.single);

      if (!mounted) return;

      if (!link.isLinked) {
        setState(() {
          _busy = false;
          _error =
              'La vinculación no quedó activa. Genera un nuevo QR en el POS.';
        });
        return;
      }

      Navigator.of(context).pop<ScannerLink>(link);
    } on AuthApiException catch (error) {
      if (!mounted) return;

      setState(() {
        _busy = false;
        _error = error.message;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _busy = false;
        _error =
            'No pudimos confirmar la vinculación. '
            'Revisa su estado en el POS antes de intentarlo nuevamente.';
      });
    }
  }

  void _retry() {
    setState(() {
      _error = null;
    });
  }

  Widget _message({
    required IconData icon,
    required String text,
    bool retry = false,
  }) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 52, color: const Color(0xFF702583)),
            const SizedBox(height: 20),
            Text(
              text,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                height: 1.5,
                color: Color(0xFF26332D),
              ),
            ),
            if (retry) ...[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _retry,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Escanear nuevamente'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_busy,
      child: Scaffold(
        backgroundColor: const Color(0xFFF5F7F6),
        appBar: AppBar(
          title: const Text('Vincular con el POS'),
          automaticallyImplyLeading: !_busy,
        ),
        body: SafeArea(
          child: Column(
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(24, 16, 24, 20),
                child: Text(
                  'En el computador, abre Vincular sesión y apunta '
                  'al QR. Usa la misma cuenta en ambos dispositivos.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 15,
                    height: 1.5,
                    color: Color(0xFF526159),
                  ),
                ),
              ),
              Expanded(
                child: _busy
                    ? const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(),
                            SizedBox(height: 20),
                            Text('Confirmando vinculación…'),
                          ],
                        ),
                      )
                    : _error != null
                    ? _message(icon: Icons.link_off, text: _error!, retry: true)
                    : Padding(
                        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(24),
                          child: MobileScanner(
                            onDetect: _onDetect,
                            errorBuilder: (context, error) {
                              return ColoredBox(
                                color: Colors.white,
                                child: _message(
                                  icon: Icons.no_photography_outlined,
                                  text:
                                      error.errorCode ==
                                          MobileScannerErrorCode
                                              .permissionDenied
                                      ? 'Permite el acceso a la cámara '
                                            'en los ajustes de la app '
                                            'y vuelve a abrir esta pantalla.'
                                      : 'No pudimos abrir la cámara. '
                                            'Cierra esta pantalla '
                                            'e inténtalo nuevamente.',
                                ),
                              );
                            },
                          ),
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
