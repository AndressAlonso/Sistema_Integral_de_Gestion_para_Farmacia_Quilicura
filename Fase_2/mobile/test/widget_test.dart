import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sigfq_mobile/main.dart';

void main() {
  testWidgets('Vinculación y lectura manual conservan ceros', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: ScannerPage()));

    final manual = find.widgetWithText(
      OutlinedButton,
      'Ingresar código manualmente',
    );

    expect(tester.widget<OutlinedButton>(manual).onPressed, isNull);

    await tester.tap(find.text('Vincular'));
    await tester.pumpAndSettle();

    await tester.tap(manual);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Registrar'));
    await tester.pumpAndSettle();
    expect(find.text('Ingresa un código.'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField), '000000000001');
    await tester.tap(find.text('Registrar'));
    await tester.pumpAndSettle();

    expect(find.text('000000000001'), findsOneWidget);
    expect(find.byType(AlertDialog), findsNothing);

    await tester.tap(find.text('Desvincular'));
    await tester.pumpAndSettle();

    expect(find.text('000000000001'), findsNothing);
    expect(tester.widget<OutlinedButton>(manual).onPressed, isNull);
  });
}
