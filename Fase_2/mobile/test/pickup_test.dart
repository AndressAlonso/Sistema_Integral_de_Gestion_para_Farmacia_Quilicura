import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sigfq_mobile/auth_api.dart';
import 'package:sigfq_mobile/pickup_page.dart';

class FakePickupApi extends AuthApi {
  int confirmations = 0;
  bool failFirst = true;
  final List<String?> expectedIds = [];
  @override
  Future<Map<String, dynamic>> pickupOrder(
    String code, {
    String? expectedOrderId,
  }) async {
    expectedIds.add(expectedOrderId);
    if (expectedOrderId != null) {
      confirmations++;
      if (failFirst) {
        failFirst = false;
        throw const AuthApiException('Conexión interrumpida');
      }
    }
    return {
      'id': 'pedido-1',
      'number': 'WEB-1',
      'status': expectedOrderId == null ? 'LISTO_PARA_RETIRO' : 'RETIRADO',
      'total': '1000',
      'pickup_branch': {'name': 'Centro'},
      'items': [
        {'name': 'Producto', 'quantity': 2},
      ],
    };
  }
}

void main() {
  testWidgets('valida sin entregar y reintenta la entrega del mismo pedido', (
    tester,
  ) async {
    final api = FakePickupApi();
    addTearDown(api.dispose);
    await tester.pumpWidget(MaterialApp(home: PickupPage(api: api)));
    await tester.enterText(find.byType(TextField), '1234567890123456');
    await tester.ensureVisible(find.text('Validar pedido'));
    await tester.tap(find.text('Validar pedido'));
    await tester.pumpAndSettle();
    expect(find.text('2 × Producto'), findsOneWidget);
    expect(api.confirmations, 0);
    await tester.scrollUntilVisible(find.byType(CheckboxListTile), 150);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Confirmar entrega'));
    await tester.tap(find.text('Confirmar entrega'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Reintentar confirmación'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reintentar confirmación'));
    await tester.pumpAndSettle();
    expect(find.text('Retiro registrado'), findsOneWidget);
    expect(api.expectedIds, [null, 'pedido-1', 'pedido-1']);
    expect(find.text('Confirmar entrega'), findsNothing);
  });
}
