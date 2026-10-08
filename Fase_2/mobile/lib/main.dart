import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'auth_gate.dart';
import 'barcode_camera_page.dart';

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
    centerTitle: false,
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
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: Color(0xFFDDE4DF)),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(
        color: pharmacyGreen,
        width: 1.5,
      ),
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
      side: const BorderSide(color: Color(0xFFDFD7E4)),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
    ),
  ),
),
      home: AuthGate(scannerBuilder: (_) => const ScannerPage()),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  bool _linked = false;
  String? _lastCode;

  void _toggleConnection() {
    setState(() {
      _linked = !_linked;
      _lastCode = null;
    });
  }

  void _recordCode(String code) {
    if (!mounted || !_linked) return;
    setState(() => _lastCode = code);
  }

  Future<void> _openCamera() async {
    if (!_linked) return;

    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => BarcodeCameraPage(onRead: _recordCode),
      ),
    );
  }

  Future<void> _manualEntry() async {
    if (!_linked) return;

    final controller = TextEditingController();
    final formKey = GlobalKey<FormState>();

    try {
      final code = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          void submit() {
            if (formKey.currentState!.validate()) {
              Navigator.of(dialogContext).pop(controller.text.trim());
            }
          }

          return AlertDialog(
            title: const Text('Ingresar código'),
            content: Form(
              key: formKey,
              child: TextFormField(
                controller: controller,
                autofocus: true,
                autocorrect: false,
                enableSuggestions: false,
                maxLength: 128,
                textInputAction: TextInputAction.done,
                decoration: const InputDecoration(
                  labelText: 'Código de barras',
                ),
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
                child: const Text('Registrar'),
              ),
            ],
          );
        },
      );

      if (code != null) _recordCode(code);
    } finally {
      // Espera a que termine la animación de salida del diálogo.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        controller.dispose();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 60,
        centerTitle: false,
        leadingWidth: 64,
        leading: Padding(
          padding: const EdgeInsets.all(8),
          child: Image.asset(
            'assets/isotipo-farmacia.png',
            fit: BoxFit.contain,
            excludeFromSemantics: true,
          ),
        ),
        title: const Text(
          'Escáner de productos',
          style: TextStyle(
            fontSize: 19,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Row(
                children: [
                  Icon(Icons.science_outlined, size: 18, color: pharmacyPurple),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Modo de prueba · POS simulado',
                      style: TextStyle(color: pharmacyPurple, fontSize: 12),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 8, 4, 8),
                  child: Row(
                    children: [
                      Icon(
                        _linked ? Icons.link : Icons.link_off,
                        color: _linked ? pharmacyGreen : pharmacyPurple,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _linked
                              ? 'Caja de prueba vinculada'
                              : 'Vincula una caja',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      TextButton(
                        onPressed: _toggleConnection,
                        child: Text(_linked ? 'Desvincular' : 'Vincular'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Expanded(
  child: Container(
    width: double.infinity,
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(
        color: const Color(0xFFE3E9E5),
      ),
      boxShadow: const [
        BoxShadow(
          color: Color(0x08000000),
          blurRadius: 20,
          offset: Offset(0, 6),
        ),
      ],
    ),
    child: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxHeight < 280;

        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Flexible(
              child: Center(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Container(
                    width: compact ? 84 : 112,
                    height: compact ? 84 : 112,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF3EDF6),
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: Icon(
                      Icons.qr_code_scanner_rounded,
                      size: compact ? 44 : 58,
                      color: pharmacyPurple,
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(height: compact ? 12 : 22),
            const Text(
              'Escanea un producto',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF26332D),
                fontSize: 22,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _linked
                  ? 'Coloca el código frente a la cámara.'
                  : 'Vincula una caja para comenzar.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF748078),
                fontSize: 14,
                height: 1.4,
              ),
            ),
            SizedBox(height: compact ? 16 : 26),
            FilledButton.icon(
              onPressed: _linked ? _openCamera : null,
              icon: const Icon(Icons.camera_alt_outlined, size: 20),
              label: const Text(
                'Abrir cámara',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        );
      },
    ),
  ),
),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _linked ? _manualEntry : null,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
                icon: const Icon(Icons.keyboard_outlined),
                label: const Text('Ingresar código manualmente'),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFEAF3E7),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
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
                                : 'Última lectura · recepción simulada',
                            style: const TextStyle(
                              color: pharmacyGreen,
                              fontSize: 12,
                            ),
                          ),
                          if (_lastCode != null)
                            Text(
                              _lastCode!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
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
    );
  }
}
