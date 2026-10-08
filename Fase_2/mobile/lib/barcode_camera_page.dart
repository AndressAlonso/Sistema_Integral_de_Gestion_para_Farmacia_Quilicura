import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class BarcodeCameraPage extends StatefulWidget {
  const BarcodeCameraPage({required this.onRead, super.key});

  final ValueChanged<String> onRead;

  @override
  State<BarcodeCameraPage> createState() => _BarcodeCameraPageState();
}

class _BarcodeCameraPageState extends State<BarcodeCameraPage> {
  String? _code;

  void _onDetect(BarcodeCapture capture) {
    if (!mounted || _code != null) return;
    if (ModalRoute.of(context)?.isCurrent != true) return;

    final codes = capture.barcodes
        .map((barcode) => barcode.rawValue)
        .whereType<String>()
        .where((code) => code.trim().isNotEmpty)
        .toSet();

    if (codes.length != 1) return;

    final code = codes.single;

    // El bloqueo se establece antes de recibir otro fotograma.
    setState(() => _code = code);
    widget.onRead(code);
  }

  @override
  Widget build(BuildContext context) {
    final code = _code;

    return Scaffold(
      backgroundColor: const Color(0xFF211729),
      appBar: AppBar(
        title: const Text('Escanear producto'),
        backgroundColor: const Color(0xFF211729),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: code == null
            ? Column(
                children: [
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Apunta a un solo código de barras',
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: MobileScanner(
                        onDetect: _onDetect,
                        useAppLifecycleState: true,
                        errorBuilder: (context, error) {
                          final denied =
                              error.errorCode ==
                              MobileScannerErrorCode.permissionDenied;

                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Text(
                                denied
                                    ? 'Permite el acceso a la cámara desde '
                                          'los ajustes de la aplicación y '
                                          'vuelve a abrir el lector.'
                                    : 'No se pudo abrir la cámara. '
                                          'Vuelve e intenta nuevamente.',
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: Colors.white),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: Text(
                      'Lectura real · POS simulado',
                      style: TextStyle(color: Colors.white70),
                    ),
                  ),
                ],
              )
            : Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Icon(
                          Icons.check_circle_rounded,
                          color: Color(0xFF437D36),
                          size: 72,
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          '¡Código leído!',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Color(0xFF702583),
                            fontSize: 26,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        SelectableText(
                          code,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 18),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Recepción simulada. No se ha agregado '
                          'ningún producto a una venta.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.black54),
                        ),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: () => setState(() => _code = null),
                          icon: const Icon(Icons.qr_code_scanner),
                          label: const Text('Escanear otro'),
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('Salir de la cámara'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }
}
