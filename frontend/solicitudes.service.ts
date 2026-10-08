import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, InjectionToken, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

// Mismo contrato que app/schemas.py del backend.
export type Categoria = 'facturacion' | 'tecnico' | 'comercial' | 'otro';
export type Prioridad = 'alta' | 'media' | 'baja';

export interface AnalizarRequest {
  id: string;
  texto: string;
  cliente_id: string;
}

export interface AnalisisResponse {
  id: string;
  cliente_id: string;
  texto: string;
  categoria: Categoria;
  prioridad: Prioridad;
  respuesta_sugerida: string;
  cliente_info: Record<string, unknown> | null;
  tokens_entrada: number;
  tokens_salida: number;
  costo_estimado: number;
  creado_en: string;
}

/**
 * URL base de la API. Vacía por defecto: en desarrollo las peticiones van al mismo origen y el proxy
 * de Angular (`proxy.conf.json`) las reenvía a http://localhost:8000, porque el backend no habilita CORS.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => '',
});

@Injectable({ providedIn: 'root' })
export class SolicitudesService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  /** Emite el análisis o falla con un `Error` cuyo mensaje se puede mostrar al usuario tal cual. */
  analizar(solicitud: AnalizarRequest): Observable<AnalisisResponse> {
    return this.http
      .post<AnalisisResponse>(`${this.baseUrl}/solicitudes/analizar`, solicitud)
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => new Error(mensajeDeError(err)))));
  }
}

function mensajeDeError(err: HttpErrorResponse): string {
  switch (err.status) {
    case 0:
      return 'No se pudo conectar con el servicio. Revise su conexión e intente de nuevo.';
    case 422:
      return mensajeDeValidacion(err.error?.detail);
    case 502:
      return 'El análisis no se pudo completar. Intente de nuevo en unos minutos.';
    default:
      return `Error inesperado del servicio (${err.status}).`;
  }
}

// FastAPI responde 422 con `detail: [{ loc: ['body', 'texto'], msg, type }, ...]`.
function mensajeDeValidacion(detail: unknown): string {
  if (!Array.isArray(detail)) {
    return 'Los datos enviados no son válidos.';
  }
  const campos = [...new Set(detail.map((d: { loc?: unknown[] }) => d.loc?.at(-1)).filter(Boolean))];
  return campos.length
    ? `Revise los campos: ${campos.join(', ')}.`
    : 'Los datos enviados no son válidos.';
}
