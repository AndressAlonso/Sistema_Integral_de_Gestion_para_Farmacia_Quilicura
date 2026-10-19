import 'dart:math';

class ScannerRead {
  const ScannerRead({
    required this.id,
    required this.linkId,
    required this.code,
    required this.result,
    required this.productId,
  });

  final String id;
  final String linkId;
  final String code;
  final String result;
  final String? productId;

  bool get productFound => result == 'FOUND';

  factory ScannerRead.fromJson(Map<String, dynamic> json) {
    final result = json['result'] as String;
    final productId = json['product_id'] as String?;

    if (!{'FOUND', 'NOT_FOUND', 'INACTIVE'}.contains(result)) {
      throw const FormatException('Resultado de lectura desconocido.');
    }

    if (result == 'NOT_FOUND' && productId != null) {
      throw const FormatException('Resultado de lectura inconsistente.');
    }

    if (result != 'NOT_FOUND' && (productId == null || productId.isEmpty)) {
      throw const FormatException('Falta el producto de la lectura.');
    }

    return ScannerRead(
      id: json['id'] as String,
      linkId: json['link_id'] as String,
      code: json['code'] as String,
      result: result,
      productId: productId,
    );
  }
}

class ScannerReadRequest {
  const ScannerReadRequest({
    required this.id,
    required this.linkId,
    required this.code,
  });

  final String id;
  final String linkId;
  final String code;

  factory ScannerReadRequest.create({
    required String linkId,
    required String code,
  }) {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));

    // UUID versión 4.
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    final hex = bytes
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join();

    final id =
        '${hex.substring(0, 8)}-'
        '${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-'
        '${hex.substring(16, 20)}-'
        '${hex.substring(20)}';

    return ScannerReadRequest(id: id, linkId: linkId, code: code);
  }
}
