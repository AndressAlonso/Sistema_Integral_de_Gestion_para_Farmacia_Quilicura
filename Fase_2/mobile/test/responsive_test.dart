import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sigfq_mobile/auth_api.dart';
import 'package:sigfq_mobile/main.dart';
import 'package:sigfq_mobile/pickup_page.dart';

void main() {
  for (final size in [
    const Size(320, 568),
    const Size(844, 390),
    const Size(1024, 768),
  ]) {
    testWidgets('Pantallas sin desbordes a $size y texto grande', (
      tester,
    ) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = AuthApi();
      addTearDown(api.dispose);
      for (final page in [
        const MyApp(),
        ScannerPage(api: api),
        PickupPage(api: api),
      ]) {
        await tester.pumpWidget(
          MaterialApp(
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context)
                  .copyWith(textScaler: const TextScaler.linear(1.5)),
              child: child!,
            ),
            home: page,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          tester.takeException(),
          isNull,
          reason: page.runtimeType.toString(),
        );
        await tester.pumpWidget(const SizedBox());
      }
    });
  }
}
