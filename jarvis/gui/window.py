"""JARVIS floating window — modern dark UI with customtkinter."""
import os
import asyncio
import threading
import tkinter as tk
import customtkinter as ctk
from dotenv import load_dotenv

load_dotenv()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = os.getenv("ACCENT_COLOR", "#00d4ff")
OPACITY = float(os.getenv("WINDOW_OPACITY", "0.95"))
JARVIS_NAME = os.getenv("JARVIS_NAME", "JARVIS")


class JarvisWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._visible = False
        self._thinking = False
        self._loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._async_thread.start()

        self._build_ui()
        self._setup_hotkey()
        self._start_wake_word()
        self._schedule_update_check()

        # Start hidden
        self.withdraw()

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.title(JARVIS_NAME)
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", OPACITY)
        self.overrideredirect(False)

        # Position: center of screen
        w, h = 520, 600
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(fg_color="#0d0d0d")

        # ── Header ────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=50)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=f"● {JARVIS_NAME}", font=ctk.CTkFont("Courier New", 16, "bold"),
            text_color=ACCENT
        ).pack(side="left", padx=15, pady=10)

        self._status_label = ctk.CTkLabel(
            header, text="pronto", font=ctk.CTkFont("Courier New", 11),
            text_color="#666666"
        )
        self._status_label.pack(side="left", padx=5)

        ctk.CTkButton(
            header, text="✕", width=30, height=30, fg_color="transparent",
            hover_color="#330000", text_color="#666666", corner_radius=4,
            command=self.hide, font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=10)

        ctk.CTkButton(
            header, text="⚙", width=30, height=30, fg_color="transparent",
            hover_color="#1a1a2e", text_color="#666666", corner_radius=4,
            command=self._open_settings, font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=2)

        # ── Chat area ─────────────────────────────────────────────
        self._chat_frame = ctk.CTkScrollableFrame(
            self, fg_color="#080808", corner_radius=8
        )
        self._chat_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # ── Input area ────────────────────────────────────────────
        input_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=8)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        self._input = ctk.CTkTextbox(
            input_frame, height=60, fg_color="#1a1a1a", border_color="#333333",
            border_width=1, corner_radius=6, font=ctk.CTkFont("Segoe UI", 13),
            text_color="#e0e0e0", wrap="word"
        )
        self._input.pack(fill="x", padx=8, pady=8, side="left", expand=True)
        self._input.bind("<Return>", self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)

        btns = ctk.CTkFrame(input_frame, fg_color="transparent")
        btns.pack(side="right", padx=6, pady=8)

        self._mic_btn = ctk.CTkButton(
            btns, text="🎤", width=40, height=40, fg_color="#1a1a2e",
            hover_color="#2a2a4e", corner_radius=6,
            command=self._listen_now, font=ctk.CTkFont(size=16)
        )
        self._mic_btn.pack(pady=(0, 4))

        ctk.CTkButton(
            btns, text="↑", width=40, height=40, fg_color=ACCENT,
            hover_color="#0099bb", text_color="#000000", corner_radius=6,
            command=self._send, font=ctk.CTkFont(size=16, weight="bold")
        ).pack()

        # Make window draggable
        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    # ── Chat messages ─────────────────────────────────────────────

    def _add_message(self, text: str, role: str):
        is_user = role == "user"
        bubble_color = "#1a1a2e" if is_user else "#0d1a0d"
        text_color = "#b0c4de" if is_user else "#90ee90"
        anchor = "e" if is_user else "w"
        prefix = "Você  " if is_user else f"{JARVIS_NAME}  "

        frame = ctk.CTkFrame(self._chat_frame, fg_color="transparent")
        frame.pack(fill="x", pady=3)

        bubble = ctk.CTkFrame(frame, fg_color=bubble_color, corner_radius=10)
        bubble.pack(anchor=anchor, padx=6)

        ctk.CTkLabel(
            bubble, text=prefix, font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=ACCENT if not is_user else "#7a9cc2"
        ).pack(anchor="w", padx=10, pady=(6, 0))

        ctk.CTkLabel(
            bubble, text=text, wraplength=380, justify="left",
            font=ctk.CTkFont("Segoe UI", 13), text_color=text_color,
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(2, 8))

        # Scroll to bottom
        self.after(50, lambda: self._chat_frame._parent_canvas.yview_moveto(1.0))

    def _add_tool_indicator(self, tool_name: str, detail: str = ""):
        labels = {
            "open_app": "🚀 Abrindo aplicativo...",
            "open_url": "🌐 Abrindo navegador...",
            "web_search": "🔍 Pesquisando...",
            "set_volume": "🔊 Ajustando volume...",
            "take_screenshot": "📸 Capturando tela...",
            "create_file": "📄 Criando arquivo...",
            "read_file": "📖 Lendo arquivo...",
            "run_command": "⚡ Executando comando...",
            "system_info": "💻 Verificando sistema...",
            "remember": "🧠 Memorizando...",
        }
        text = labels.get(tool_name, f"🔧 {tool_name}...")
        frame = ctk.CTkFrame(self._chat_frame, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        ctk.CTkLabel(
            frame, text=text, font=ctk.CTkFont("Segoe UI", 11, "italic"),
            text_color="#444444"
        ).pack(anchor="w", padx=16)

    def _show_thinking(self):
        self._thinking_frame = ctk.CTkFrame(self._chat_frame, fg_color="transparent")
        self._thinking_frame.pack(fill="x", pady=3)
        self._thinking_label = ctk.CTkLabel(
            self._thinking_frame,
            text="● ● ●",
            font=ctk.CTkFont("Courier New", 14),
            text_color="#444444"
        )
        self._thinking_label.pack(anchor="w", padx=16)
        self._animate_thinking()

    def _animate_thinking(self, step=0):
        if not self._thinking or not hasattr(self, "_thinking_label"):
            return
        frames = ["●  ·  ·", "·  ●  ·", "·  ·  ●", "·  ●  ·"]
        try:
            self._thinking_label.configure(text=frames[step % len(frames)])
        except Exception:
            return
        self.after(300, lambda: self._animate_thinking(step + 1))

    def _hide_thinking(self):
        self._thinking = False
        if hasattr(self, "_thinking_frame"):
            try:
                self._thinking_frame.destroy()
            except Exception:
                pass

    # ── Actions ───────────────────────────────────────────────────

    def _on_enter(self, event):
        if not event.state & 0x1:  # Shift not held
            self._send()
            return "break"

    def _send(self):
        text = self._input.get("1.0", "end").strip()
        if not text:
            return
        self._input.delete("1.0", "end")
        self._add_message(text, "user")
        self._run_async(self._process(text))

    def _listen_now(self):
        self._set_status("ouvindo...")
        self._mic_btn.configure(fg_color="#002200", text_color="#00ff00")

        def _listen():
            from jarvis.voice.listener import listen_once
            text = listen_once(timeout=8)
            self.after(0, self._mic_btn.configure, {"fg_color": "#1a1a2e", "text_color": "white"})
            if text:
                self.after(0, self._add_message, text, "user")
                self.after(0, self._set_status, "processando...")
                self._run_async(self._process(text))
            else:
                self.after(0, self._set_status, "não ouvi nada")

        threading.Thread(target=_listen, daemon=True).start()

    async def _process(self, text: str):
        self.after(0, self._set_status, "pensando...")
        self._thinking = True
        self.after(0, self._show_thinking)

        from jarvis.brain.ai import chat_stream

        response_chunks = []

        def on_chunk(chunk):
            response_chunks.append(chunk)

        def on_tool(name, detail):
            self.after(0, self._hide_thinking)
            self.after(0, self._add_tool_indicator, name, detail)

        try:
            full = await chat_stream(text, on_chunk=on_chunk, on_tool=on_tool)
            self.after(0, self._hide_thinking)
            self.after(0, self._add_message, full, "assistant")
            self.after(0, self._set_status, "pronto")

            # TTS
            tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
            if tts_enabled and full:
                from jarvis.voice.tts import speak
                speak(full[:300])  # Speak up to 300 chars
        except Exception as e:
            self.after(0, self._hide_thinking)
            self.after(0, self._add_message, f"Erro: {e}", "assistant")
            self.after(0, self._set_status, "erro")

    def _set_status(self, text: str):
        self._status_label.configure(text=text)

    # ── Visibility ────────────────────────────────────────────────

    def show(self):
        if not self._visible:
            self._visible = True
            self.deiconify()
            self.lift()
            self.focus_force()
            self._input.focus_set()

    def hide(self):
        if self._visible:
            self._visible = False
            self.withdraw()

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    # ── Hotkey ────────────────────────────────────────────────────

    def _setup_hotkey(self):
        hotkey = os.getenv("HOTKEY", "alt+space")
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, lambda: self.after(0, self.toggle))
        except Exception as e:
            print(f"[Hotkey] Erro: {e}")

    # ── Wake word ─────────────────────────────────────────────────

    def _start_wake_word(self):
        wake_enabled = os.getenv("WAKE_WORD_ENABLED", "true").lower() == "true"
        if not wake_enabled:
            return
        try:
            from jarvis.voice.listener import start_wake_word_listener
            start_wake_word_listener(lambda: self.after(0, self._on_wake))
        except Exception as e:
            print(f"[WakeWord] Erro: {e}")

    def _on_wake(self):
        self.show()
        self._set_status("ouvindo (wake)...")
        self._listen_now()

    # ── Settings ──────────────────────────────────────────────────

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Configurações")
        win.geometry("400x400")
        win.attributes("-topmost", True)
        win.configure(fg_color="#0d0d0d")

        ctk.CTkLabel(win, text="Configurações do JARVIS",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=ACCENT).pack(pady=15)

        fields = [
            ("Seu nome", "USER_NAME", "user_name"),
            ("Voz TTS", "TTS_VOICE", None),
            ("Tecla de atalho", "HOTKEY", None),
            ("Palavra de ativação", "WAKE_WORD", None),
        ]

        entries = {}
        for label, env_key, pref_key in fields:
            f = ctk.CTkFrame(win, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(f, text=label, width=130, anchor="w",
                         font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(side="left")
            entry = ctk.CTkEntry(f, font=ctk.CTkFont(size=12))
            entry.insert(0, os.getenv(env_key, ""))
            entry.pack(side="left", fill="x", expand=True)
            entries[env_key] = entry

        def save():
            env_path = os.path.join(os.path.dirname(__file__), "../../.env")
            lines = []
            if os.path.exists(env_path):
                with open(env_path) as f:
                    lines = f.readlines()
            for env_key, entry in entries.items():
                val = entry.get().strip()
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(f"{env_key}="):
                        lines[i] = f"{env_key}={val}\n"
                        found = True
                        break
                if not found:
                    lines.append(f"{env_key}={val}\n")
            with open(env_path, "w") as f:
                f.writelines(lines)
            ctk.CTkLabel(win, text="✓ Salvo! Reinicie para aplicar.",
                         text_color="#00ff00").pack(pady=5)

        ctk.CTkButton(win, text="Salvar", command=save,
                      fg_color=ACCENT, text_color="#000000",
                      font=ctk.CTkFont(weight="bold")).pack(pady=15)

    # ── Update check ─────────────────────────────────────────────

    def _schedule_update_check(self):
        if os.getenv("AUTO_UPDATE", "true").lower() != "true":
            return
        self.after(10000, self._check_update)  # 10s after start

    def _check_update(self):
        def _check():
            from jarvis.updater.updater import check_for_update
            new_ver = check_for_update()
            if new_ver:
                self.after(0, self._prompt_update, new_ver)

        threading.Thread(target=_check, daemon=True).start()
        # Check again in 1 hour
        self.after(3600000, self._schedule_update_check)

    def _prompt_update(self, new_ver: dict):
        self._add_message(
            f"Nova versão disponível: {new_ver['version']}. "
            f"Digite 'atualizar' para instalar.",
            "assistant"
        )

    # ── Async loop ────────────────────────────────────────────────

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self._loop)
