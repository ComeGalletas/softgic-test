import { DatePipe, DecimalPipe, KeyValuePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { AnalisisResponse, SolicitudesService } from './solicitudes.service';

// Pruebas previstas: ver analizar-solicitud.component.spec.ts.
@Component({
  selector: 'app-analizar-solicitud',
  standalone: true,
  imports: [ReactiveFormsModule, DatePipe, DecimalPipe, KeyValuePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="enviar()">
      <label>
        ID de la solicitud
        <input formControlName="id" maxlength="100" />
      </label>
      @if (form.controls.id.touched && form.controls.id.invalid) {
        <small class="campo-error">Obligatorio, máximo 100 caracteres.</small>
      }

      <label>
        ID del cliente
        <input formControlName="cliente_id" maxlength="100" />
      </label>
      @if (form.controls.cliente_id.touched && form.controls.cliente_id.invalid) {
        <small class="campo-error">Obligatorio, máximo 100 caracteres.</small>
      }

      <label>
        Texto de la solicitud
        <textarea formControlName="texto" rows="5" maxlength="10000"></textarea>
      </label>
      @if (form.controls.texto.touched && form.controls.texto.invalid) {
        <small class="campo-error">Obligatorio, máximo 10.000 caracteres.</small>
      }

      <button type="submit" [disabled]="cargando()">
        {{ cargando() ? 'Analizando…' : 'Analizar' }}
      </button>
    </form>

    @if (cargando()) {
      <p class="estado" role="status">Analizando la solicitud…</p>
    }

    @if (error(); as mensaje) {
      <p class="error" role="alert">{{ mensaje }}</p>
    }

    @if (resultado(); as r) {
      <section class="resultado" aria-live="polite">
        <h2>Resultado de {{ r.id }}</h2>
        <p>
          <span class="etiqueta">{{ r.categoria }}</span>
          <span class="etiqueta" [attr.data-prioridad]="r.prioridad">Prioridad {{ r.prioridad }}</span>
        </p>

        <h3>Respuesta sugerida</h3>
        <!-- La interpolación escapa el HTML: el texto del modelo nunca se inserta como marcado. -->
        <blockquote>{{ r.respuesta_sugerida }}</blockquote>

        <h3>Cliente {{ r.cliente_id }}</h3>
        @if (r.cliente_info; as info) {
          <dl>
            @for (campo of info | keyvalue; track campo.key) {
              <dt>{{ campo.key }}</dt>
              <dd>{{ campo.value }}</dd>
            }
          </dl>
        } @else {
          <p class="nota">Sin datos del CRM (solo se consultan para prioridad alta o el CRM no respondió).</p>
        }

        <p class="nota">
          {{ r.tokens_entrada }} tokens de entrada · {{ r.tokens_salida }} de salida ·
          USD {{ r.costo_estimado | number: '1.2-8' }} · {{ r.creado_en | date: 'short' }}
        </p>
      </section>
    }
  `,
  styles: `
    :host { display: block; max-width: 40rem; font-family: system-ui, sans-serif; }
    form { display: grid; gap: 0.5rem; }
    label { display: grid; gap: 0.25rem; font-weight: 600; }
    input, textarea { font: inherit; padding: 0.4rem; }
    button { justify-self: start; padding: 0.4rem 1rem; }
    .campo-error, .error { color: #b00020; }
    .error { border: 1px solid currentColor; padding: 0.5rem; }
    .estado, .nota { color: #555; }
    .resultado { margin-top: 1rem; }
    .etiqueta { display: inline-block; margin-right: 0.5rem; padding: 0.1rem 0.6rem; border-radius: 1rem; background: #e8eaf6; }
    .etiqueta[data-prioridad='alta'] { background: #ffcdd2; }
    .etiqueta[data-prioridad='media'] { background: #fff3c4; }
    .etiqueta[data-prioridad='baja'] { background: #c8e6c9; }
    blockquote { margin: 0; padding: 0.5rem 1rem; border-left: 4px solid #9fa8da; white-space: pre-line; }
    dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; }
    dt { font-weight: 600; }
    dd { margin: 0; }
  `,
})
export class AnalizarSolicitudComponent {
  private readonly solicitudes = inject(SolicitudesService);
  private readonly destroyRef = inject(DestroyRef);

  // Mismos límites que AnalizarRequest en el backend.
  readonly form = inject(NonNullableFormBuilder).group({
    id: ['', [Validators.required, Validators.maxLength(100)]],
    cliente_id: ['', [Validators.required, Validators.maxLength(100)]],
    texto: ['', [Validators.required, Validators.maxLength(10_000)]],
  });

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly resultado = signal<AnalisisResponse | null>(null);

  enviar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.cargando()) {
      return;
    }

    this.cargando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.solicitudes
      .analizar(this.form.getRawValue())
      .pipe(
        finalize(() => this.cargando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (r) => this.resultado.set(r),
        error: (e: Error) => this.error.set(e.message),
      });
  }
}
