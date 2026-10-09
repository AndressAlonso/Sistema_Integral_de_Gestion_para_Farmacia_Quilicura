import 'package:cookie_jar/cookie_jar.dart';
import 'package:dio/dio.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';

import 'scanner_link.dart';

class AuthSession {
  const AuthSession({
    required this.userId,
    required this.name,
    required this.email,
    required this.branchId,
    required this.branchName,
    required this.permissions,
    required this.roles,
    required this.expiresAt,
  });

  final String userId;
  final String name;
  final String email;
  final String branchId;
  final String branchName;
  final List<String> permissions;
  final List<String> roles;
  final DateTime expiresAt;

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>;

    return AuthSession(
      userId: user['id'] as String,
      name: user['name'] as String,
      email: user['email'] as String,
      branchId: user['branch_id'] as String,
      branchName: user['branch_name'] as String,
      permissions: List<String>.unmodifiable(
        user['permissions'] as List<dynamic>,
      ),
      roles: List<String>.unmodifiable(user['roles'] as List<dynamic>),
      expiresAt: DateTime.parse(json['expires_at'] as String),
    );
  }
}

class AuthApiException implements Exception {
  const AuthApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class AuthApi {
  AuthApi()
    : _dio = Dio(
        BaseOptions(
          baseUrl: const String.fromEnvironment(
            'API_BASE_URL',
            defaultValue: 'http://127.0.0.1:8000',
          ),
          connectTimeout: const Duration(seconds: 10),
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
          contentType: Headers.jsonContentType,
          responseType: ResponseType.json,
          followRedirects: false,
          headers: {'Accept': 'application/json'},
        ),
      ) {
    _dio.interceptors.add(CookieManager(_cookies));
  }

  final Dio _dio;
  final CookieJar _cookies = CookieJar();

  Future<AuthSession> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/auth/login',
        data: {'email': email.trim(), 'password': password},
      );

      return _readSession(response.data);
    } on DioException catch (error) {
      throw _translateError(error);
    }
  }

  Future<AuthSession> currentSession() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/auth/me');

      return _readSession(response.data);
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        await _cookies.deleteAll();
      }
      throw _translateError(error);
    }
  }

  Future<void> logout() async {
    try {
      await _dio.post<void>('/api/auth/logout');

      // Borramos la cookie tras confirmar el cierre en el servidor.
      await _cookies.deleteAll();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        await _cookies.deleteAll();
        return;
      }

      // Si falla la conexión, informamos que no se confirmó el cierre.
      throw _translateError(error);
    }
  }

  AuthSession _readSession(Map<String, dynamic>? data) {
    try {
      if (data == null) {
        throw const FormatException('Respuesta vacía');
      }

      return AuthSession.fromJson(data);
    } on FormatException {
      throw const AuthApiException(
        'El servidor devolvió una sesión con formato incorrecto.',
      );
    } on TypeError {
      throw const AuthApiException(
        'El servidor devolvió una sesión incompleta.',
      );
    }
  }

  AuthApiException _translateError(DioException error) {
    final status = error.response?.statusCode;

    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return const AuthApiException(
        'El servidor tardó demasiado en responder. Intenta nuevamente.',
      );
    }

    if (error.type == DioExceptionType.connectionError) {
      return const AuthApiException(
        'No pudimos conectar con el servidor. '
        'Revisa que la API esté encendida y la conexión USB esté activa.',
      );
    }

    final data = error.response?.data;

    if (status != null && status >= 400 && status < 500) {
      if (data is Map<String, dynamic>) {
        final detail = data['detail'];

        if (detail is String && detail.isNotEmpty) {
          return AuthApiException(detail, statusCode: status);
        }
      }
    }

    return AuthApiException(
      'No pudimos completar la solicitud. Intenta nuevamente.',
      statusCode: status,
    );
  }

  Future<ScannerLink> claimScanner(String qrContent) async {
    const prefix = 'sigfq:pair:v1:';

    if (!qrContent.startsWith(prefix)) {
      throw const AuthApiException(
        'Este QR no es de vinculación. '
        'Genera uno desde el botón Vincular sesión del POS.',
      );
    }

    final code = qrContent.substring(prefix.length);

    if (!RegExp(r'^[A-Za-z0-9_-]{43}$').hasMatch(code)) {
      throw const AuthApiException(
        'El código de vinculación tiene un formato incorrecto.',
      );
    }

    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/scanner/links/claim',
        data: {'pairing_code': code},
      );

      return _readScannerLink(response.data);
    } on DioException catch (error) {
      throw _translateError(error);
    }
  }

  Future<ScannerLink> scannerStatus(String linkId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/scanner/links/${Uri.encodeComponent(linkId)}',
      );

      return _readScannerLink(response.data);
    } on DioException catch (error) {
      throw _translateError(error);
    }
  }

  Future<ScannerLink> revokeScanner(String linkId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/scanner/links/${Uri.encodeComponent(linkId)}/revoke',
      );

      return _readScannerLink(response.data);
    } on DioException catch (error) {
      throw _translateError(error);
    }
  }

  ScannerLink _readScannerLink(Map<String, dynamic>? data) {
    try {
      if (data == null) {
        throw const FormatException('Respuesta vacía');
      }

      final link = ScannerLink.fromJson(data);

      const states = {
        'PENDING',
        'LINKED',
        'REVOKED',
        'EXPIRED',
        'DISCONNECTED',
      };

      if (!states.contains(link.state)) {
        throw const FormatException('Estado desconocido');
      }

      return link;
    } on FormatException {
      throw const AuthApiException(
        'El servidor devolvió una vinculación con formato incorrecto.',
      );
    } on TypeError {
      throw const AuthApiException(
        'El servidor devolvió una vinculación incompleta.',
      );
    }
  }

  void dispose() {
    _dio.close(force: true);
  }
}
