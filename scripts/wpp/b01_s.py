import csv
import time
import os
import re
import keyboard  # Para detectar teclas
from pathlib import Path
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

#TIME_LIMIT_SECONDS = 5 * 60  # 5 minutos
MAX_NON_GROUP_CHAT = 250  # Valor por defecto, se puede modificar en ejecución
CHAT_TIME_LIMIT_SECONDS = 60  #  por chat

EXCLUDE_TITLES = {
    "Rosmery Papel Asesora de Viajes Terandes",
    "Canal Comercial y Ventas | TLA CTA",
    "Salida fija Mex - Setiembre / 2025",
    "Salida fija Mex-Julio/Agosto",
    "Marketing Digital CTA TLA",
    "Ross Mery Asesora De Ventas",
    "Christian TLA",
    "Tierras de los andes",
    "TLA - CTA - ITT",
    "Marketing Team 🎸 TLA- CTA",
    "Ventas Interno",
    "OPERACIONES TERANDES",
    "Estrella Asesora de viajes a Perú",
    "VENTAS REDES SOCIALES INTERNO- LEADS Mercado Latino",
    "WhatsApp Business",
    "CULTURAS ANDINAS",
    "Salida fija Mex - Setiembre / 2025 🇲🇽✈️🇵🇪",
    "Salida fija Mex-Julio/Agosto",
    "Salida fija Mex - Octubre 2025 🥳🙌🏻",
    "Notas 🐸",
    "Facebook",
    "Sistemas Rodrigo",
    "Año Nuevo en Perú - MÉXICO",
    "Viagem Cuzco",
    "AÑO NUEVO EN PERÚ - COSTA RICA 🇨🇷",
    "Meri Marketing",
    "Milu Operaciones Tla Cusco",
    "Christian",
    "Juana Tierra De Los Andes",
    "Claribel Tierra de los Andes",
    "Estrella grupo",
    "Peru",
    "+51 913 579 325",
    "Michel Tla",
    "Milusca Operaciones Cusco",
    "Juan Corporativo",
    "Debora Hotel Tla Empresa",
    "Arielys X4 Septiembre",
    "Renato Ventas",
    "Rosmery Quispe Corporativo",
    "+51 978 877 833",
    "Adriel Trenes",
    "Vanessa X6 Mayo",
    "Ascencio Monarga TLA Personal",
    "Daniel Tla Inca",
    "Karina Vuelos TLA",
    "Sra Juanita Personal",
    "Rodrigo Empresa",
    "José Daniel Montero X2 Febrero",
    "Loren Marie Puerto x1",
    "Omar Mex",
    "Rosmery Cuba TLA",
    "Angela Número",
}
META_BANNED_CHARS = {"*", "#", "•"} 

# ======================================================
# 1) DRIVER (perfil persistente)
# ======================================================

def setup_driver(profile_name="wpp1"):
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # ✅ Carpeta base con múltiples perfiles
    base_dir = os.path.join(os.path.expanduser("~"), "whatsapp_selenium_profiles")
    os.makedirs(base_dir, exist_ok=True)

    # ✅ Un directorio distinto por perfil
    profile_dir = os.path.join(base_dir, profile_name)
    os.makedirs(profile_dir, exist_ok=True)

    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)




def wait_for_whatsapp_login(driver):
    print("\n" + "=" * 60)
    print("INICIA SESIÓN EN WHATSAPP WEB")
    print("1) Escanea el QR si es necesario")
    print("2) Espera a que cargue la lista de chats")
    print("3) Vuelve aquí y presiona ENTER")
    print("=" * 60 + "\n")
    input("Presiona ENTER cuando WhatsApp Web esté listo...")

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )


# ======================================================
# 2) WHATSAPP – PRIMER CHAT
# ======================================================

def get_first_chat_name(driver):
    pane = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )
    spans = pane.find_elements(By.XPATH, ".//span[@title]")

    for s in spans:
        title = (s.get_attribute("title") or "").strip()
        if title:
            return title
    return None


def open_chat_by_title(driver, contact):
    user = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, f'//*[@id="pane-side"]//span[contains(@title, "{contact}")]')
        )
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", user)
    user.click()
    time.sleep(2)

def get_visible_chat_titles(driver):
    """
    Devuelve los títulos (nombres) de chats visibles en el panel izquierdo,
    en el orden en que aparecen (WhatsApp: más recientes arriba).
    """
    pane = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )
     # Filas del listado de chats (WhatsApp suele usar role="row")
    rows = pane.find_elements(By.XPATH, ".//div[@role='row']")

    titles = []
    seen = set()

    for row in rows:
        try:
            # Dentro de cada fila, el nombre/número del chat casi siempre es el primer span con title
            name_span = row.find_element(By.XPATH, ".//span[@title and normalize-space(@title)!='']")
            title = (name_span.get_attribute("title") or "").strip()

            if not title:
                continue
            if "\n" in title:
                continue
            if len(title) > 60:
                continue
            if title in ("Archivados", "WhatsApp"):
                continue

            if title not in seen:
                seen.add(title)
                titles.append(title)

        except Exception:
            # Si esa fila no tiene span title “usable”, la saltamos
            continue

    return titles
    


def scroll_left_pane(driver, step=900):
    """
    Baja el panel izquierdo para cargar chats más antiguos.
    """
    pane = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + arguments[1];", pane, step)
    time.sleep(1.2)
########################################## normalizar titulo
def norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()
EXCLUDE_TITLES_NORM = {norm_title(t) for t in EXCLUDE_TITLES}
######################################## detector del banner
def end_to_end_banner_present(driver) -> bool:
    """
    True si aparece banner de corte dentro del chat:
    - E2E
    - Banner corporativo Meta Admin
    """
    try:
        scroller = get_chat_scroller(driver)

        e2e = scroller.find_elements(
            By.XPATH,
            ".//*[contains(., 'Los mensajes y las llamadas están cifrados de extremo a extremo')]"
        )

        meta_admin = scroller.find_elements(
            By.XPATH,
            ".//*[contains(., 'Tu empresa usa un servicio seguro de Meta para administrar este chat')]"
        )

        return bool(e2e) or bool(meta_admin)
    except Exception:
        return False

# ======================================================
# 3) FECHA (si luego quieres filtrar)
# ======================================================

def parse_date_from_meta(meta: str):
    if not meta:
        return None
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", meta)
    if not m:
        return None

    d1, d2, y = m.group(1), m.group(2), m.group(3)
    y = int("20" + y) if len(y) == 2 else int(y)

    day = int(d1)
    month = int(d2)

    try:
        return datetime(y, month, day).date()
    except ValueError:
        return None


# ======================================================
# 4) CLICK "mensajes anteriores del teléfono"
# ======================================================

def click_load_older_if_present(driver):
    """
    Si aparece el aviso: 'Haz clic aquí para obtener mensajes anteriores de tu teléfono',
    hace click y espera. Devuelve True si clickeó.
    """
    try:
        # Caso común: un botón que contiene ese texto
        btns = driver.find_elements(
            By.XPATH,
            "//button[.//div[contains(., 'Haz clic aquí para obtener mensajes anteriores')]]"
        )
        if btns:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btns[0])
            time.sleep(0.3)
            btns[0].click()
            time.sleep(2.5)
            return True

        # Fallback: a veces es un div/spam clickeable
        divs = driver.find_elements(
            By.XPATH,
            "//*[contains(., 'Haz clic aquí para obtener mensajes anteriores') and (self::div or self::span)]"
        )
        if divs:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", divs[0])
            time.sleep(0.3)
            divs[0].click()
            time.sleep(2.5)
            return True

    except Exception:
        pass

    return False




#################################################################################################################### scroller

def get_chat_scroller(driver):
    """
    Contenedor REAL que scrollea los mensajes del chat.
    (confirmado por tu consola: policy 'wa.web.conversation.messages')
    """
    return WebDriverWait(driver, 25).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.copyable-area [data-scrolltracepolicy='wa.web.conversation.messages']")
        )
    )

def get_scroll_metrics(driver, el):
    return driver.execute_script(
        "return {st: arguments[0].scrollTop, sh: arguments[0].scrollHeight, ch: arguments[0].clientHeight};",
        el
    )
def scroll_chat_step(driver, scroller):
    # métricas
    st = driver.execute_script("return arguments[0].scrollTop;", scroller) or 0
    sh = driver.execute_script("return arguments[0].scrollHeight;", scroller) or 0
    ch = driver.execute_script("return arguments[0].clientHeight;", scroller) or 0
    delta = sh - ch

    step = max(120, min(900, int(delta * 0.8)))

    if st > 5:
        driver.execute_script(
            "arguments[0].scrollTop = Math.max(0, arguments[0].scrollTop - arguments[1]);",
            scroller,
            step
        )
        time.sleep(1.2)
        return "scrolled"
    else:
        # arriba; espera a que cargue más
        time.sleep(2.5)
        return "at_top"
########################################################################################################################
def get_message_bubble_from_meta_el(meta_el):
    # sube al contenedor del mensaje (burbuja) más cercano
    return meta_el.find_element(By.XPATH, "./ancestor::div[@role='row'][1]")

######################################################### audio
def bubble_kind(bubble):
    # AUDIO: tu debug confirmó data-icon audio-play
    if bubble.find_elements(By.XPATH, ".//*[@data-icon='audio-play' or @data-icon='ptt-play']"):
        return "AUDIO"

    # ADJUNTO: fotos/docs suelen traer botones con aria-label
    if bubble.find_elements(By.XPATH, ".//*[@role='button' and contains(@aria-label,'Abrir foto')]"):
        return "ADJUNTO"
    if bubble.find_elements(By.XPATH, ".//*[@role='button' and (contains(@aria-label,'Descargar') or contains(@aria-label,'Download'))]"):
        return "ADJUNTO"
    # if bubble.find_elements(By.XPATH, ".//*[@role='button' and contains(@aria-label,'Reenviar archivo')]"):
    #     return "ADJUNTO"

    # Fallback: si no hay texto pero hay img, suele ser media
    txt = (bubble.text or "").strip()
    if not txt and bubble.find_elements(By.TAG_NAME, "img"):
        return "ADJUNTO"

    return ""


def meta_from_bubble(bubble):
    # A veces el meta está en un descendiente del mismo row
    meta_els = bubble.find_elements(By.XPATH, ".//*[@data-pre-plain-text]")
    if meta_els:
        return (meta_els[0].get_attribute("data-pre-plain-text") or "").strip()
    return ""

#-----------------------------------------------------------------
#............................................................>>>>>>>>> scrollea y recolect los mensajes dentro de un chat

def scrape_messages_from_current_chat(driver, contact, time_limit_seconds=CHAT_TIME_LIMIT_SECONDS):
    """
    Devuelve: (rows, timed_out)
      - rows: lista de dicts {contact, meta, text}
      - timed_out: True si excedió el tiempo límite (y el caller debe NO guardar este chat)
    """
    WebDriverWait(driver, 25).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.copyable-area"))
    )
    scroller = get_chat_scroller(driver)

    messages = {}
    idle = 0
    last_len = 0

    t0 = time.time()
    timed_out = False

    while True:
        # ⏱️ TIMEOUT POR CHAT
        if (time.time() - t0) > time_limit_seconds:
            print(f"⏱️ Timeout {time_limit_seconds}s en chat '{contact}'. Se omite y NO se guarda.")
            timed_out = True
            break

        # 1) TEXTOS “normales” (con meta)
        elements = scroller.find_elements(By.XPATH, "//*[@data-pre-plain-text]")
        for el in elements:
            meta = (el.get_attribute("data-pre-plain-text") or "").strip()
            text = (el.text or "").strip()

            if not meta and not text:
                continue

            key = f"{meta}||{text}"
            if key not in messages:
                messages[key] = {"contact": contact, "meta": meta, "text": text}

        # 2) AUDIOS / ADJUNTOS (sin meta directo)
        bubbles = driver.find_elements(By.XPATH, "//div[@role='row']")
        for b in bubbles:
            kind = bubble_kind(b)
            if not kind:
                continue

            meta = meta_from_bubble(b)  # probablemente vacío si WA no expone el atributo
            text = f"[{kind}]"

            preview = (b.text or "").strip().replace("\n", " ")[:80]
            key = f"{meta}||{text}||{preview}"

            if key not in messages:
                messages[key] = {"contact": contact, "meta": meta, "text": text}

        # 3) corte por banner (E2E o Meta Admin)
        if end_to_end_banner_present(driver):
            print("🧱 Banner detectado. Fin del historial alcanzado.")
            break

        # 4) Click “mensajes anteriores del teléfono” si aparece
        if click_load_older_if_present(driver):
            time.sleep(1.8)
            continue

        # 5) scroll un paso arriba
        scroll_chat_step(driver, scroller)

        # 6) watchdog (SIN input para no congelar)
        if len(messages) == last_len:
            idle += 1
        else:
            idle = 0
        last_len = len(messages)

        if idle >= 30:
            print("⚠️ No está avanzando (WhatsApp no carga más).")
            idle = 0

    return list(messages.values()), timed_out


# ======================================================
# 6) CSV
# ======================================================

def save_to_csv(filename, rows):
    headers = ["contact", "meta", "text"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


# ======================================================
# 7) MAIN
# ======================================================
def main():
    profile = input("Perfil (wpp1..wpp6): ").strip().lower()
    if profile not in {"wpp1","wpp2","wpp3","wpp4","wpp5","wpp6"}:
        profile = "wpp1"
    print("✅ Usando perfil:", profile)

    driver = setup_driver(profile)
    driver.get("https://web.whatsapp.com/")
    wait_for_whatsapp_login(driver)

    # Pedir configuración al usuario
    try:
        max_chats_input = input("¿Cuántos chats no-grupo procesar? (por defecto 250): ").strip()
        if max_chats_input and max_chats_input.isdigit():
            global MAX_NON_GROUP_CHAT
            MAX_NON_GROUP_CHAT = int(max_chats_input)
            print(f"✅ Se procesarán hasta {MAX_NON_GROUP_CHAT} chats no-grupo")
        else:
            print(f"✅ Usando valor por defecto: {MAX_NON_GROUP_CHAT} chats no-grupo")
    except ValueError:
        print(f"❌ Valor inválido. Usando valor por defecto: {MAX_NON_GROUP_CHAT}")

    print("\n🛑 Para detener el scraping en cualquier momento, presiona la tecla 'q'")
    print("🔄 Iniciando scraping...")
    
    output_name = input("Nombre del archivo CSV (sin .csv): ").strip()
    safe_name = "".join(c for c in output_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "-")
    if not safe_name:
        safe_name = "todos_los_chats"

    # ▸ Ruta relativa: ../files/input/wpp  (a partir de la carpeta 'scripts')
    base_out_dir = (Path(__file__).resolve().parent.parent / "files" / "input" / "wpp")
    base_out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = str(base_out_dir / f"{safe_name}.csv")

    all_rows = []
    processed = set()

    max_rounds = 80
    pane_step = 1200

    skipped_timeouts = 0
    skipped_errors = 0
    non_group_count = 0

    timed_out_chats = []  # ✅ NUEVO: lista de chats que exceden tiempo

    print("\n🚀 Recorriendo chats: del más reciente al más antiguo...")

    try:
        for r in range(max_rounds):
            # Verificar si el usuario presionó 'q' para detener
            if keyboard.is_pressed('q'):
                print("\n🛑 Usuario detuvo el scraping con la tecla 'q'")
                break
                
            titles = get_visible_chat_titles(driver)
            print("DEBUG: titles visibles =", titles[:8], " total =", len(titles))

            new_titles = [t for t in titles if t not in processed]

            if not new_titles:
                scroll_left_pane(driver, pane_step)
                titles2 = get_visible_chat_titles(driver)
                new_titles = [t for t in titles2 if t not in processed]

                if not new_titles:
                    print("✅ No hay más chats nuevos en el panel. Terminando.")
                    break

            for title in new_titles:
                # Verificar si el usuario presionó 'q' para detener
                if keyboard.is_pressed('q'):
                    print("\n🛑 Usuario detuvo el scraping con la tecla 'q'")
                    break
                    
                if non_group_count >= MAX_NON_GROUP_CHAT:
                    print(f"🛑 Límite alcanzado: {MAX_NON_GROUP_CHAT} chats (sin contar grupos).")
                    break

                print(f"📌 Abriendo chat: {title}")

                # excluidos
                if norm_title(title) in EXCLUDE_TITLES_NORM:
                    print("⛔ En lista de excluidos. Saltando (no se scrapea).")
                    processed.add(title)
                    continue

                try:
                    open_chat_by_title(driver, title)
                    print("📩 Extrayendo mensajes...")

                    rows, timed_out = scrape_messages_from_current_chat(driver, title)

                    if timed_out:
                        skipped_timeouts += 1
                        timed_out_chats.append(title)  # ✅ NUEVO
                        print(f"⏭️ Chat omitido por timeout. Total timeouts: {skipped_timeouts}")
                        processed.add(title)
                        continue  # ✅ NO se guarda nada

                    print(f"✅ Mensajes: {len(rows)}")
                    all_rows.extend(rows)
                    processed.add(title)

                    non_group_count += 1
                    print(f"✅ Chats no-grupo procesados: {non_group_count}/{MAX_NON_GROUP_CHAT}")

                except Exception as e:
                    skipped_errors += 1
                    print(f"⚠️ Error en chat '{title}': {e} | errors={skipped_errors}")
                    processed.add(title)
                    continue

            if non_group_count >= MAX_NON_GROUP_CHAT:
                break

            scroll_left_pane(driver, pane_step)

    finally:
        print(f"\n📊 Chats procesados (incluye skips): {len(processed)}")
        print(f"📊 Mensajes totales recolectados: {len(all_rows)}")
        print(f"⏭️ Chats omitidos por timeout: {skipped_timeouts}")
        print(f"⚠️ Chats omitidos por error: {skipped_errors}")

        # ✅ NUEVO: imprimir lista de chats con timeout
        if timed_out_chats:
            print("\n⏱️ Chats que superaron el tiempo límite (NO guardados):")
            for i, t in enumerate(timed_out_chats, 1):
                print(f"  {i:02d}. {t}")
        else:
            print("\n⏱️ No hubo chats que superaran el tiempo límite.")

        # Guardar CSV
        if all_rows:
            try:
                save_to_csv(output_csv, all_rows)
                print(f"\n✅ CSV generado correctamente: {output_csv}")
            except Exception as e:
                print("⚠️ Error guardando CSV:", e)
        else:
            print("⚠️ No se recolectaron mensajes. No se generará CSV.")

        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
