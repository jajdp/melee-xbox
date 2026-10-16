/* Capa de compatibilidad del port de Melee a UWP (Decompilaciones, 2026-10-01).
 *
 * El C del juego y de la capa de PC se compila con el GCC de MinGW (scalar_storage_order) y se
 * enlaza contra el CRT «store» de MSVC. Lo que MinGW resolvía con sus propias bibliotecas
 * (libmingwex, winpthreads) se da aquí, con el mismo ABI que esperan esos objetos:
 *   - __mingw_*printf: las variantes ANSI que eligen los .c compilados en modo gnu11;
 *   - sincos: GCC funde sin(x) y cos(x) en una sola llamada (stb_vorbis);
 *   - gettimeofday (extern/dht);
 *   - pthread_mutex_... y pthread_once con los tipos de winpthreads (src/pc/audio.c: un mutex
 *     recursivo creado una sola vez);
 *   - GetUserProfileDirectoryW, que pide la std de Rust dentro de nod.lib y que en un
 *     AppContainer no existe: nod no la necesita para leer el disco.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <math.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* --- printf de MinGW ------------------------------------------------------------------------- */
int __mingw_vfprintf(FILE* f, const char* fmt, va_list ap) { return vfprintf(f, fmt, ap); }

int __mingw_fprintf(FILE* f, const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  const int r = vfprintf(f, fmt, ap);
  va_end(ap);
  return r;
}

int __mingw_vsnprintf(char* buf, size_t n, const char* fmt, va_list ap) { return vsnprintf(buf, n, fmt, ap); }

int __mingw_snprintf(char* buf, size_t n, const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  const int r = vsnprintf(buf, n, fmt, ap);
  va_end(ap);
  return r;
}

int __mingw_printf(const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  const int r = vprintf(fmt, ap);
  va_end(ap);
  return r;
}

/* --- matemáticas y tiempo -------------------------------------------------------------------- */
void sincos(double x, double* s, double* c) {
  *s = sin(x);
  *c = cos(x);
}

void sincosf(float x, float* s, float* c) {
  *s = sinf(x);
  *c = cosf(x);
}

struct compat_timeval {
  long tv_sec;
  long tv_usec;
};

int gettimeofday(struct compat_timeval* tv, void* tz) {
  (void)tz;
  if (tv != NULL) {
    FILETIME ft;
    GetSystemTimePreciseAsFileTime(&ft);
    uint64_t t = ((uint64_t)ft.dwHighDateTime << 32) | ft.dwLowDateTime; /* 100 ns desde 1601 */
    t -= 116444736000000000ULL;                                          /* a 1970 */
    tv->tv_sec = (long)(t / 10000000ULL);
    tv->tv_usec = (long)((t % 10000000ULL) / 10ULL);
  }
  return 0;
}

/* --- pthreads con los tipos de winpthreads ---------------------------------------------------- */
typedef intptr_t pthread_mutex_t;
typedef unsigned pthread_mutexattr_t;
typedef long pthread_once_t;

static CRITICAL_SECTION* mutex_de(pthread_mutex_t* m) {
  /* Un intptr_t que guarda un CRITICAL_SECTION* (recursivo, como pide audio.c). Los
   * inicializadores estáticos de winpthreads son -1, -2 y -3: se crea al primer uso. */
  intptr_t v = *m;
  if (v != 0 && v != -1 && v != -2 && v != -3) {
    return (CRITICAL_SECTION*)v;
  }
  CRITICAL_SECTION* cs = (CRITICAL_SECTION*)malloc(sizeof *cs);
  InitializeCriticalSectionEx(cs, 0, 0);
  if (InterlockedCompareExchangePointer((PVOID volatile*)m, cs, (PVOID)v) != (PVOID)v) {
    DeleteCriticalSection(cs);
    free(cs);
  }
  return (CRITICAL_SECTION*)*m;
}

int pthread_mutexattr_init(pthread_mutexattr_t* a) {
  *a = 0;
  return 0;
}
int pthread_mutexattr_settype(pthread_mutexattr_t* a, int tipo) {
  *a = (unsigned)tipo;
  return 0;
}
int pthread_mutexattr_destroy(pthread_mutexattr_t* a) {
  (void)a;
  return 0;
}
int pthread_mutex_init(pthread_mutex_t* m, const pthread_mutexattr_t* a) {
  (void)a;
  *m = 0;
  mutex_de(m);
  return 0;
}
int pthread_mutex_lock(pthread_mutex_t* m) {
  EnterCriticalSection(mutex_de(m));
  return 0;
}
int pthread_mutex_unlock(pthread_mutex_t* m) {
  LeaveCriticalSection(mutex_de(m));
  return 0;
}
int pthread_mutex_destroy(pthread_mutex_t* m) {
  intptr_t v = *m;
  if (v != 0 && v != -1 && v != -2 && v != -3) {
    DeleteCriticalSection((CRITICAL_SECTION*)v);
    free((void*)v);
  }
  *m = 0;
  return 0;
}
int pthread_once(pthread_once_t* o, void (*f)(void)) {
  /* 0 = sin hacer, 1 = en curso, 2 = hecho */
  if (InterlockedCompareExchange(o, 1, 0) == 0) {
    f();
    InterlockedExchange(o, 2);
  } else {
    while (*(volatile long*)o != 2) {
      SwitchToThread();
    }
  }
  return 0;
}

/* --- GetUserProfileDirectoryW para la std de Rust -------------------------------------------- */
static BOOL WINAPI sin_perfil(HANDLE token, LPWSTR dir, LPDWORD tam) {
  (void)token;
  (void)dir;
  (void)tam;
  SetLastError(ERROR_NOT_SUPPORTED);
  return FALSE;
}
void* __imp_GetUserProfileDirectoryW = (void*)sin_perfil;
