// Actualizador de melee-pc para UWP: vacío (Decompilaciones, 2026-10-01).
// El original descarga con WinHTTP, que no existe dentro de un AppContainer, y en la consola el
// paquete se actualiza reinstalándolo por el Device Portal. Mantiene la API de updater.hpp para
// que el lanzador compile igual: siempre «al día».
#include "pc/updater.hpp"

#include <SDL3/SDL.h>

namespace pc::updater {

void check_for_updates_async(bool) {}
void start_download_async() {}
void cancel() {}

UpdateState get_state() {
  UpdateState s;
  s.status = Status::UpToDate;
  s.message = "Updates are installed from the Xbox Device Portal";
  return s;
}

void open_release_in_browser() { SDL_OpenURL("https://github.com/999sian/melee-pc/releases"); }
void open_downloaded_location() {}

bool apply_update_and_restart(std::string& error) {
  error = "Not supported on Xbox";
  return false;
}

}  // namespace pc::updater
