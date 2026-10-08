# Frontend

Componente standalone (`analizar-solicitud.component.ts`) y servicio (`solicitudes.service.ts`) que llaman a `POST /solicitudes/analizar` y muestran la carga, los errores y el resultado.

## Token de Microsoft Entra ID

1. Registraría la API en Entra ID exponiendo un scope (`api://<id-api>/Solicitudes.Analizar`) y el frontend como aplicación SPA (cliente público, sin secreto).
2. En Angular usaría MSAL (`@azure/msal-angular`): el usuario inicia sesión con authorization code + PKCE, un flujo que no necesita secreto de cliente.
3. Registraría `MsalInterceptor` (con `provideHttpClient(withInterceptorsFromDi())`) y un `protectedResourceMap` que asocia la URL de la API con ese scope.
4. El interceptor obtiene el access token con `acquireTokenSilent` (lo renueva solo y pide interacción solo si hace falta) y agrega `Authorization: Bearer <token>` únicamente a las peticiones hacia esa URL.
5. Así el servicio y el componente no cambian, y el token nunca se envía a otros dominios.
6. En el navegador solo quedan el client ID y el tenant ID, que son identificadores públicos; la caché de tokens va en `sessionStorage` o en memoria, no en `localStorage`.
7. La API valida firma (JWKS de Entra), emisor, audiencia, expiración y scope de cada token, y responde 401 o 403 si no cumplen.
8. Cualquier secreto (por ejemplo, para llamar a otro servicio con on-behalf-of) vive solo en el backend, en Key Vault o variables de entorno.
9. Si no se quiere ningún token en el navegador, la alternativa es un BFF que hace el flujo confidencial y solo entrega una cookie `HttpOnly; Secure; SameSite`.
