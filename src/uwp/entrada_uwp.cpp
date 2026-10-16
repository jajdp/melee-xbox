// Entrada UWP del port de Melee a la Xbox (Decompilaciones, 2026-10-01).
//
// Sustituye a lib/main.cpp de Aurora. En un AppContainer el proceso arranca sin argumentos útiles,
// sin bloque de entorno y sin consola, así que antes de entrar al juego:
//   1. localiza LocalState (el Temp de la app es <paquete>\AC\Temp; LocalState está dos niveles
//      arriba) y manda stdout y stderr a LocalState\melee-salida.txt (los dos en modo «a»: con «w»
//      cada flujo lleva su posición y se pisan);
//   2. si existe LocalState\melee-env.txt, pone cada línea NOMBRE=VALOR en el entorno del CRT con
//      _putenv_s (getenv devuelve NULL en UWP, pero el CRT guarda su propia copia: truco de DKR);
//   3. busca el disco (.rvz, .iso, .gcm, .ciso) en LocalState y se lo pasa al juego como argv[1].
// Luego SDL_RunApp levanta la aplicación WinRT y llama a aurora_main (el main() de melee-pc).
#include <aurora/main.h>
#undef main

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <SDL3/SDL.h>
#define SDL_MAIN_HANDLED
#include <SDL3/SDL_main.h>

namespace {

std::wstring g_local;              // ...\LocalState\ (con barra final)
std::vector<std::string> g_args;   // argv del juego
std::vector<char*> g_argv;

std::string utf8(const std::wstring& w) {
  if (w.empty()) return {};
  const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
  std::string s(static_cast<size_t>(n > 0 ? n - 1 : 0), '\0');
  if (n > 1) WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, s.data(), n, nullptr, nullptr);
  return s;
}

void localiza_localstate() {
  wchar_t tmp[MAX_PATH]{};
  const DWORD n = GetTempPathW(MAX_PATH, tmp);
  std::wstring t(tmp, n);
  // De «Packages\<PFN>\AC\Temp» se pasa a «Packages\<PFN>\LocalState».
  if (t.size() > 8 && (t.back() == L'\\' || t.back() == L'/')) t.pop_back();
  for (int i = 0; i < 2; ++i) {
    const size_t p = t.find_last_of(L"\\/");
    if (p != std::wstring::npos) t.resize(p);
  }
  g_local = t + L"\\LocalState\\";
}

void redirige_salida() {
  const std::wstring ruta = g_local + L"melee-salida.txt";
  FILE* f = nullptr;
  _wfreopen_s(&f, ruta.c_str(), L"a", stdout);
  _wfreopen_s(&f, ruta.c_str(), L"a", stderr);
  setvbuf(stdout, nullptr, _IONBF, 0);
  setvbuf(stderr, nullptr, _IONBF, 0);
  std::printf("=== melee-uwp: arranque ===\n");
}

void carga_entorno() {
  // Valores por defecto: el registro del juego, a LocalState.
  const std::string log = utf8(g_local + L"melee.log");
  _putenv_s("MELEE_LOG_FILE", log.c_str());
  FILE* f = nullptr;
  if (_wfopen_s(&f, (g_local + L"melee-env.txt").c_str(), L"r") != 0 || f == nullptr) {
    std::printf("melee-env.txt: no hay\n");
    return;
  }
  char linea[1024];
  while (std::fgets(linea, sizeof linea, f) != nullptr) {
    char* s = linea;
    while (*s == ' ' || *s == '\t') ++s;
    if (*s == '#' || *s == '\n' || *s == '\r' || *s == '\0') continue;
    char* eq = std::strchr(s, '=');
    if (eq == nullptr) continue;
    *eq = '\0';
    char* v = eq + 1;
    size_t len = std::strlen(v);
    while (len > 0 && (v[len - 1] == '\n' || v[len - 1] == '\r' || v[len - 1] == ' ')) v[--len] = '\0';
    _putenv_s(s, v);
    std::printf("env: %s=%s\n", s, v);
  }
  std::fclose(f);
}

// El Device Portal respondió 500 al subir el disco de Melee entero (RVZ de 1,06 GiB) y en partes
// de 900 MiB; en partes de 250 MiB, no. Se sube partido en «<nombre>.parte1», «<nombre>.parte2»…
// y aquí se une, una sola vez (las partes se quedan; el juego solo lee el archivo unido).
void une_partes() {
  WIN32_FIND_DATAW d{};
  HANDLE h = FindFirstFileExW((g_local + L"*.parte1").c_str(), FindExInfoBasic, &d, FindExSearchNameMatch, nullptr, 0);
  if (h == INVALID_HANDLE_VALUE) return;
  FindClose(h);
  std::wstring base(d.cFileName);
  base.resize(base.size() - std::wcslen(L".parte1"));
  const std::wstring destino = g_local + base;
  if (GetFileAttributesW(destino.c_str()) != INVALID_FILE_ATTRIBUTES) return;  // ya unido
  const std::wstring tmp = destino + L".uniendo";
  FILE* out = nullptr;
  if (_wfopen_s(&out, tmp.c_str(), L"wb") != 0 || out == nullptr) {
    std::printf("partes: no se pudo crear %s\n", utf8(tmp).c_str());
    return;
  }
  std::vector<char> buf(8u << 20);
  unsigned long long total = 0;
  for (int i = 1;; ++i) {
    const std::wstring parte = destino + L".parte" + std::to_wstring(i);
    FILE* in = nullptr;
    if (_wfopen_s(&in, parte.c_str(), L"rb") != 0 || in == nullptr) break;
    size_t n;
    while ((n = std::fread(buf.data(), 1, buf.size(), in)) > 0) {
      std::fwrite(buf.data(), 1, n, out);
      total += n;
    }
    std::fclose(in);
    std::printf("partes: unida %s\n", utf8(parte).c_str());
  }
  std::fclose(out);
  if (MoveFileExW(tmp.c_str(), destino.c_str(), MOVEFILE_REPLACE_EXISTING)) {
    std::printf("partes: %s listo (%llu bytes)\n", utf8(destino).c_str(), total);
  } else {
    std::printf("partes: no se pudo renombrar (error %lu)\n", GetLastError());
  }
}

std::string busca_disco() {
  une_partes();
  static const wchar_t* extensiones[] = {L"*.rvz", L"*.iso", L"*.gcm", L"*.ciso"};
  for (const wchar_t* ext : extensiones) {
    WIN32_FIND_DATAW d{};
    HANDLE h = FindFirstFileExW((g_local + ext).c_str(), FindExInfoBasic, &d, FindExSearchNameMatch, nullptr, 0);
    if (h != INVALID_HANDLE_VALUE) {
      FindClose(h);
      return utf8(g_local + d.cFileName);
    }
  }
  return {};
}

int Juego(int, char**) {
  std::printf("SDL_RunApp: entrando a aurora_main con %zu argumentos\n", g_args.size());
  return aurora_main(static_cast<int>(g_argv.size()) - 1, g_argv.data());
}

} // namespace

int CALLBACK WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
  localiza_localstate();
  redirige_salida();
  carga_entorno();
  g_args.push_back("melee");
  const std::string disco = busca_disco();
  if (!disco.empty()) {
    g_args.push_back(disco);
    std::printf("disco: %s\n", disco.c_str());
  } else {
    std::printf("disco: ninguno en LocalState (se abrirá el lanzador)\n");
  }
  for (auto& a : g_args) g_argv.push_back(a.data());
  g_argv.push_back(nullptr);
  // En la consola, B es también el «atrás» del sistema: si nadie lo atiende, cierra la app. Con
  // esta pista SDL lo atiende y la pulsación sigue llegando al juego por Windows.Gaming.Input.
  SDL_SetHintWithPriority(SDL_HINT_WINRT_HANDLE_BACK_BUTTON, "1", SDL_HINT_OVERRIDE);
  // Los mandos de la consola solo llegan por Windows.Gaming.Input, y el SDL3 de UWP lo trae apagado
  // por defecto (SDL_HINT_JOYSTICK_WGI = "0"): sin esta pista SDL no ve ningún mando y el juego no
  // responde a nada (paquete 0.1.4.0). Mario Kart Wii y Dusklight UWP lo encienden igual.
  SDL_SetHintWithPriority(SDL_HINT_JOYSTICK_WGI, "1", SDL_HINT_OVERRIDE);
  return SDL_RunApp(0, nullptr, Juego, nullptr);
}
