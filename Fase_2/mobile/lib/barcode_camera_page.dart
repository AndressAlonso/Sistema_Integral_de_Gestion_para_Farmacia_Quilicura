import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'auth_api.dart';
import 'scanner_read.dart';

class BarcodeCameraPage extends StatefulWidget {
  const BarcodeCameraPage({
    super.key,
    required this.api,
    required this.linkId,
    required this.onSent,
    required this.onPendingChanged,
    this.pendingRead,
    this.initialCode,
  });

  final AuthApi api;
  final String linkId;
  final ValueChanged<ScannerRead> onSent;
  final ValueChanged<ScannerReadRequest?> onPendingChanged;
  final ScannerReadRequest? pendingRead;
  final String? initialCode;

  @override
  State<BarcodeCameraPage> createState() => _BarcodeCameraPageState();
}

class _BarcodeCameraPageState extends State<BarcodeCameraPage> {
  ScannerReadRequest? _request;
  ScannerRead? _result;
  bool _sending = false;
  bool _retryable = true;
  bool _invalidCode = false;
  String? _error;

  @override
  void initState() {
    super.initState();

    _request = widget.pendingRead;

    if (_request != null) {
      _error =
          'Esta lectura quedó pendiente de confirmación. '
          'Reintenta el mismo envío.';
    } else if (widget.initialCode != null) {
      _request = ScannerReadRequest.create(
        linkId: widget.linkId,
        code: widget.initialCode!,
      );

      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        widget.onPendingChanged(_request);
        _send();
      });
    }
  }

  void _onDetect(BarcodeCapture capture) {
    if (!mounted || _request != null || _sending) return;
    if (ModalRoute.of(context)?.isCurrent != true) return;

    final codes = capture.barcodes
        .map((barcode) => barcode.rawValue)
        .whereType<String>()
        .where((code) => code.trim().isNotEmpty)
        .toSet();

    if (codes.length != 1) return;

    final request = ScannerReadRequest.create(
      linkId: widget.linkId,
      code: codes.single,
    );

    // Bloquea otros fotogramas antes de enviar.
    setState(() {
      _request = request;
      _result = null;
      _error = null;
      _retryable = true;
      _invalidCode = false;
    });

    widget.onPendingChanged(request);
    _send();
  }

  Future<void> _send() async {
    final request = _request;
    if (_sending || request == null || _result != null) return;

    setState(() {
      _sending = true;
      _error = null;
    });

    try {
      if (request.linkId != widget.linkId) {
        throw const AuthApiException(
          'La lectura pertenece a otra vinculación.',
          statusCode: 409,
        );
      }

      final result = await widget.api.submitScannerRead(
        linkId: request.linkId,
        requestId: request.id,
        code: request.code,
      );

      if (!mounted) return;

      setState(() {
        _result = result;
      });

      widget.onPendingChanged(null);
      widget.onSent(result);
    } on AuthApiException catch (error) {
      if (!mounted) return;

      final terminal = {401, 403, 404, 409, 422}.contains(error.statusCode);

      setState(() {
        _error = error.message;
        _retryable = !terminal;
        _invalidCode = error.statusCode == 422;
      });

      if (terminal) {
        widget.onPendingChanged(null);
      }
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _error =
            'No pudimos confirmar el envío. '
            'Reintenta esta misma lectura.';
        _retryable = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  void _scanAnother() {
    setState(() {
      _request = null;
      _result = null;
      _error = null;
      _retryable = true;
      _invalidCode = false;
    });
  }

  String get _resultMessage {
    switch (_result?.result) {
      case 'FOUND':
        return 'El servidor recibió el código. '
            'Revisa el POS para confirmar que se agregó al carrito.';
      case 'NOT_FOUND':
        return 'Este código no está asociado a un producto del catálogo.';
      case 'INACTIVE':
        return 'El producto está desactivado y no se agregará al carrito.';
      default:
        return '';
    }
  }

  Widget _camera() {
    return Column(
      children: [
        const Padding(
          padding: EdgeInsets.all(20),
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
              errorBuilder: (context, error) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      error.errorCode == MobileScannerErrorCode.permissionDenied
                          ? 'Permite el acceso a la cámara en los ajustes '
                                'de la app y vuelve a abrir el lector.'
                          : 'No pudimos abrir la cámara. '
                                'Vuelve e inténtalo nuevamente.',
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
            'Los códigos se enviarán al POS vinculado.',
            style: TextStyle(color: Colors.white70),
          ),
        ),
      ],
    );
  }

  Widget _feedback() {
    final success = _result?.productFound ?? false;
    final canContinue = _result != null || _invalidCode;

    return Center(
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
              if (_sending)
                const Center(child: CircularProgressIndicator())
              else
                Icon(
                  success
                      ? Icons.check_circle_rounded
                      : Icons.info_outline_rounded,
                  color: success
                      ? const Color(0xFF437D36)
                      : const Color(0xFF702583),
                  size: 64,
                ),
              const SizedBox(height: 20),
              Text(
                _sending
                    ? 'Enviando código…'
                    : _error != null
                    ? 'Revisa el envío'
                    : success
                    ? 'Código recibido'
                    : 'Producto no disponible',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF26332D),
                ),
              ),
              const SizedBox(height: 12),
              SelectableText(
                _request!.code,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 16),
              Text(
                _sending
                    ? 'Espera la respuesta del servidor.'
                    : _error ?? _resultMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF526159), height: 1.5),
              ),
              if (!_sending) ...[
                const SizedBox(height: 24),
                if (_error != null && _retryable)
                  FilledButton.icon(
                    onPressed: _send,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar envío'),
                  ),
                if (canContinue)
                  FilledButton.icon(
                    onPressed: _scanAnother,
                    icon: const Icon(Icons.qr_code_scanner),
                    label: const Text('Escanear otro'),
                  ),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Salir de la cámara'),
                ),
                if (_error != null && _retryable) ...[
                  const SizedBox(height: 12),
                  const Text(
                    'Si sales, conservaremos esta lectura pendiente '
                    'mientras la app siga abierta.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_sending,
      child: Scaffold(
        backgroundColor: const Color(0xFF211729),
        appBar: AppBar(
          title: const Text('Escanear producto'),
          automaticallyImplyLeading: !_sending,
          backgroundColor: const Color(0xFF211729),
          foregroundColor: Colors.white,
        ),
        body: SafeArea(child: _request == null ? _camera() : _feedback()),
      ),
    );
  }
}
