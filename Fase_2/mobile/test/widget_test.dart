import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sigfq_mobile/auth_api.dart';
import 'package:sigfq_mobile/main.dart';

void main() {
  testWidgets('Sin vinculación no permite leer productos', (tester) async {
    final api = AuthApi();
    addTearDown(api.dispose);

    await tester.pumpWidget(MaterialApp(home: ScannerPage(api: api)));

    expect(find.text('Vincula una caja'), findsOneWidget);

    final cameraButton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Abrir cámara'),
    );

    final manualButton = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Ingresar código manualmente'),
    );

    expect(cameraButton.onPressed, isNull);
    expect(manualButton.onPressed, isNull);
  });

  test('Rechaza códigos que no son de vinculación', () async {
    final api = AuthApi();
    addTearDown(api.dispose);

    await expectLater(
      api.claimScanner('000000000001'),
      throwsA(isA<AuthApiException>()),
    );
  });
}
