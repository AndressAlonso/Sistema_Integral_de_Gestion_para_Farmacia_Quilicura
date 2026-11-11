import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'auth_api.dart';

/// E8-H2: validar primero; entregar solo tras confirmación explícita.
class PickupPage extends StatefulWidget {
  const PickupPage({super.key, required this.api});
  final AuthApi api;
  @override
  State<PickupPage> createState() => _PickupPageState();
}

class _PickupPageState extends State<PickupPage> {
  final _input = TextEditingController();
  String? _code, _error;
  Map<String, dynamic>? _order;
  bool _camera = false, _busy = false, _done = false, _reviewed = false;
  bool _uncertain = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _request({bool confirm = false, String? scanned}) async {
    if (_busy || _done || (confirm && (!_reviewed || _order == null))) return;
    final code = confirm ? _code! : (scanned ?? _input.text).trim();
    if (code.isEmpty) return;
    setState(() {
      _busy = true;
      _camera = false;
      _error = null;
      _code = code;
    });
    try {
      final result = await widget.api.pickupOrder(
        code,
        expectedOrderId: confirm ? _order!['id'] as String : null,
      );
      if (!mounted) return;
      setState(() {
        _order = result;
        _done = confirm;
        _uncertain = false;
      });
    } on AuthApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _uncertain =
            confirm && (error.statusCode == null || error.statusCode! >= 500);
        if (!_uncertain) {
          _order = null;
          _reviewed = false;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error =
            'No pudimos confirmar la respuesta. Reintenta la misma operación.';
        _uncertain = confirm;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  void _reset() {
    _input.clear();
    setState(() {
      _order = null;
      _code = null;
      _error = null;
      _done = false;
      _reviewed = false;
      _uncertain = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    return PopScope(
      canPop: !_busy && !_uncertain,
      child: Scaffold(
        appBar: AppBar(title: const Text('Retirar pedido')),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 600),
              child: ListView(
                padding: EdgeInsets.all(
                  MediaQuery.sizeOf(context).width < 360 ? 16 : 24,
                ),
                children: [
                  const Center(
                    child: CircleAvatar(
                      radius: 32,
                      backgroundColor: Color(0xFFF3EDF6),
                      child: Icon(
                        Icons.inventory_2_outlined,
                        size: 32,
                        color: Color(0xFF702583),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Retiro de compras online',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Escanea el QR del cliente y revisa los productos antes de entregar.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      height: 1.5,
                      color: Color(0xFF526159),
                    ),
                  ),
                  const SizedBox(height: 20),
                  if (_busy) const LinearProgressIndicator(),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Text(
                        _error!,
                        semanticsLabel: 'Error: $_error',
                        style: const TextStyle(color: Color(0xFFB42318)),
                      ),
                    ),
                  if (order == null) ...[
                    if (_camera)
                      SizedBox(
                        height: 260,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: MobileScanner(
                            onDetect: (capture) {
                              if (_busy ||
                                  !_camera ||
                                  ModalRoute.of(context)?.isCurrent != true) {
                                return;
                              }
                              final codes = capture.barcodes
                                  .map((b) => b.rawValue)
                                  .whereType<String>()
                                  .where((v) => v.isNotEmpty)
                                  .toSet();
                              if (codes.length == 1) {
                                _request(scanned: codes.single);
                              }
                            },
                            errorBuilder: (context, error) => const Center(
                              child: Text(
                                'No se pudo abrir la cámara. Revisa el permiso o ingresa el código manualmente.',
                              ),
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                              _camera = !_camera;
                            }),
                      icon: Icon(_camera ? Icons.close : Icons.qr_code_scanner),
                      label: Text(_camera ? 'Cerrar cámara' : 'Escanear QR'),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      '¿No puedes escanear?',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Ingresa el código que aparece debajo del QR del cliente.',
                      style: TextStyle(color: Color(0xFF526159), height: 1.5),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _input,
                      enabled: !_busy,
                      maxLength: 100,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: const InputDecoration(
                        labelText: 'Código de retiro',
                        hintText: 'Código de 16 dígitos',
                        prefixIcon: Icon(Icons.dialpad),
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _request(),
                    ),
                    OutlinedButton(
                      onPressed: _busy ? null : () => _request(),
                      child: const Text('Validar pedido'),
                    ),
                  ],
                  if (order != null) ...[
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              _done
                                  ? Icons.check_circle
                                  : Icons.inventory_2_outlined,
                              color: _done
                                  ? Colors.green
                                  : const Color(0xFF702583),
                              size: 36,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              _done
                                  ? 'Retiro registrado'
                                  : 'Pedido listo para entregar',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Text(order['number'] as String),
                            Text('Sucursal: ${order['pickup_branch']['name']}'),
                            const Divider(height: 28),
                            for (final item in order['items'] as List)
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 6,
                                ),
                                child: Text(
                                  '${item['quantity']} × ${item['name']}',
                                ),
                              ),
                            const Divider(height: 28),
                            Text(
                              'Total pagado: CLP ${order['total']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (!_done) ...[
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _reviewed,
                        onChanged: _busy || _uncertain
                            ? null
                            : (value) => setState(() {
                                _reviewed = value ?? false;
                              }),
                        title: const Text(
                          'Revisé los productos y confirmo su entrega.',
                        ),
                      ),
                      if (_uncertain)
                        const Text(
                          'La respuesta quedó pendiente. Reintenta la confirmación; el servidor evita registrar dos retiros.',
                        ),
                      FilledButton.icon(
                        onPressed: !_busy && _reviewed
                            ? () => _request(confirm: true)
                            : null,
                        icon: const Icon(Icons.check),
                        label: Text(
                          _uncertain
                              ? 'Reintentar confirmación'
                              : 'Confirmar entrega',
                        ),
                      ),
                    ],
                    if (!_busy && !_uncertain)
                      TextButton(
                        onPressed: _reset,
                        child: Text(
                          _done
                              ? 'Retirar otro pedido'
                              : 'Escanear otro pedido',
                        ),
                      ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
