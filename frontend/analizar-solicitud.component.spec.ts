// Archivo vacío a propósito: el enunciado solo pide el componente y el servicio, y sin un proyecto
// de Angular estas pruebas no se pueden ejecutar. Con un proyecto las escribiría con
// provideHttpClientTesting() y HttpTestingController sobre POST /solicitudes/analizar:
//
// - Formulario inválido: no envía la petición y marca los campos como tocados.
// - Mientras la petición está pendiente: cargando() es true y el botón está deshabilitado.
// - 200: muestra categoría, prioridad, respuesta sugerida, datos del cliente, tokens y costo.
// - 200 con cliente_info null: muestra la nota "Sin datos del CRM".
// - 422: muestra "Revise los campos: ..." con los campos que devuelve FastAPI.
// - 502 y error de red (status 0): muestran su mensaje y limpian el resultado anterior.
// - La respuesta sugerida con HTML se muestra como texto, no como marcado.
