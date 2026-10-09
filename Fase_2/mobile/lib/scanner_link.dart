class ScannerLink {
  const ScannerLink({
    required this.id,
    required this.state,
    required this.cashId,
    required this.branchId,
    required this.expiresAt,
  });

  final String id;
  final String state;
  final String cashId;
  final String branchId;
  final DateTime expiresAt;

  bool get isLinked => state == 'LINKED';

  factory ScannerLink.fromJson(Map<String, dynamic> json) {
    return ScannerLink(
      id: json['id'] as String,
      state: json['state'] as String,
      cashId: json['cash_id'] as String,
      branchId: json['branch_id'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
    );
  }
}
