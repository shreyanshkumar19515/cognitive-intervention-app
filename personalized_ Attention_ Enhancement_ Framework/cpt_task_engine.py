import os
import sys
import time
import random
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Cross-platform winsound handling
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# =============================================================================
# EXPERIMENTAL TIMING CONSTANTS (Seconds)
# =============================================================================
DISTRACTOR_1_START = 480.0    # Minute 8: 65 dB Distractor Burst #1 Start
DISTRACTOR_1_END = 540.0      # Minute 9: Distractor Burst #1 End
DISTRACTOR_2_START = 720.0    # Minute 12: 65 dB Distractor Burst #2 Start
DISTRACTOR_2_END = 780.0      # Minute 13: Distractor Burst #2 End
QUESTION_TIMEOUT_SEC = 15.0   # 15 seconds per extract-based item

# =============================================================================
# ANCIENT CIVILIZATION EXTRACTS & ISOMORPHIC TASK GENERATOR
# =============================================================================
EXTRACTS = {
    "Task 0": (
        "ANCIENT EGYPTIAN MATHEMATICS (Rhind Papyrus Rule):\n"
        "The Egyptians represented multiplication by repeated doubling. "
        "To multiply N by 5, double N (N*2), double that (N*4), and add N to (N*4)."
    ),
    "Task A": (
        "ANCIENT BABYLONIAN MATHEMATICS (Sexagesimal Rule):\n"
        "The Babylonians calculated using base-60. A 'Susu' equals 60 units. "
        "To evaluate a sexagesimal pair [M, N], calculate total units as: (M * 60) + N."
    ),
    "Task B": (
        "ANCIENT VEDIC MATHEMATICS (Sutra Ekadhikena Rule):\n"
        "To square a number ending in 5 (e.g., N5 where tens digit is D), "
        "multiply D by (D + 1) to get the prefix, and append 25 to the end."
    )
}

class AncientMathTaskGenerator:
    """Generates extract-based questions adhering to isomorphic difficulty bounds."""
    @staticmethod
    def generate_item(task_variant: str) -> Dict[str, Any]:
        variant = task_variant.upper()

        if "TASK 0" in variant:
            n = random.randint(12, 45)
            ans = n * 5
            prompt = f"EXTRACT RULE (Egyptian Doubling):\nApply: Multiply {n} by 5 using the Doubling Rule [(N*4) + N]."
            distractor_offsets = random.sample([-20, -10, -5, 5, 10, 20], 3)

        elif "TASK A" in variant:
            m = random.randint(2, 9)
            n = random.randint(10, 49)
            ans = (m * 60) + n
            prompt = f"EXTRACT RULE (Babylonian Sexagesimal):\nEvaluate sexagesimal pair [{m}, {n}] where total = ({m} * 60) + {n}."
            distractor_offsets = random.sample([-30, -15, -10, 10, 15, 30], 3)

        else: # TASK B
            d = random.randint(2, 9)
            num = (d * 10) + 5
            ans = (d * (d + 1)) * 100 + 25
            prompt = f"EXTRACT RULE (Vedic Squaring):\nSquare the number {num}^2 using rule [D * (D + 1)] appended with 25."
            # Distractors for Task B also end in 25 to preserve task difficulty
            distractor_offsets = random.sample([-200, -100, -300, 100, 200, 300], 3)

        options = [ans] + [ans + offset for offset in distractor_offsets]
        random.shuffle(options)

        return {
            "prompt": prompt,
            "correct_answer": ans,
            "options": options
        }

# =============================================================================
# MAIN CPT TASK GUI ENGINE
# =============================================================================
class CPTTaskApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Personalized Attention Enhancement Framework - Ancient Math Engine")
        self.root.geometry("900x700")
        self.root.configure(bg="#1E1E1E")

        self.participant_id = ""
        self.task_variant = "Task 0"
        self.session_duration_sec = 600
        self.is_running = False
        self.start_time_epoch = 0.0
        self.current_item = {}
        self.item_start_time = 0.0
        self.trial_counter = 0
        self.distractor_active = False
        self.timeout_job: Optional[str] = None
        self.telemetry_records: List[Dict[str, Any]] = []

        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        # Header Controls
        self.config_frame = tk.Frame(self.root, bg="#2D2D2D", pady=12, padx=15)
        self.config_frame.pack(fill="x")

        tk.Label(self.config_frame, text="Participant ID:", fg="#FFFFFF", bg="#2D2D2D", font=("Helvetica", 11, "bold")).grid(row=0, column=0, padx=5)
        self.pid_entry = tk.Entry(self.config_frame, font=("Helvetica", 11), width=10)
        self.pid_entry.insert(0, "P001")
        self.pid_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.config_frame, text="Task Variant:", fg="#FFFFFF", bg="#2D2D2D", font=("Helvetica", 11, "bold")).grid(row=0, column=2, padx=5)
        self.task_combo = ttk.Combobox(self.config_frame, values=["Task 0", "Task A", "Task B"], width=10, state="readonly", font=("Helvetica", 11))
        self.task_combo.set("Task 0")
        self.task_combo.grid(row=0, column=3, padx=5)

        self.start_btn = tk.Button(self.config_frame, text=" ▶ START SESSION", bg="#28A745", fg="#FFFFFF", font=("Helvetica", 11, "bold"), command=self.start_session)
        self.start_btn.grid(row=0, column=4, padx=15)

        # Status Display
        self.status_frame = tk.Frame(self.root, bg="#1E1E1E", pady=8)
        self.status_frame.pack(fill="x")

        self.timer_label = tk.Label(self.status_frame, text="Elapsed Time: 00:00", fg="#00E5FF", bg="#1E1E1E", font=("Consolas", 13, "bold"))
        self.timer_label.pack(side="left", padx=20)

        self.distractor_label = tk.Label(self.status_frame, text="Acoustic Distractor: INACTIVE", fg="#6C757D", bg="#1E1E1E", font=("Helvetica", 11, "bold"))
        self.distractor_label.pack(side="right", padx=20)

        # Reference Extract Box
        self.extract_box = tk.LabelFrame(self.root, text=" ANCIENT MATHEMATICS EXTRACT REFERENCE ", fg="#FFD700", bg="#252526", font=("Helvetica", 10, "bold"), padx=15, pady=10)
        self.extract_box.pack(fill="x", padx=20, pady=5)

        self.extract_text = tk.Label(self.extract_box, text="Select Task Variant and click START SESSION.", fg="#E0E0E0", bg="#252526", font=("Georgia", 11, "italic"), wraplength=820, justify="left")
        self.extract_text.pack()

        # Question Card
        self.card_frame = tk.Frame(self.root, bg="#2D2D2D", bd=2, relief="groove", pady=20, padx=20)
        self.card_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.prompt_label = tk.Label(self.card_frame, text="Question prompt will appear here.", fg="#FFFFFF", bg="#2D2D2D", font=("Helvetica", 14, "bold"), wraplength=750, justify="center")
        self.prompt_label.pack(pady=15)

        # Multiple Choice Buttons
        self.options_frame = tk.Frame(self.card_frame, bg="#2D2D2D")
        self.options_frame.pack(pady=10)

        self.option_buttons = []
        for i in range(4):
            btn = tk.Button(self.options_frame, text="", font=("Helvetica", 13, "bold"), width=14, bg="#007ACC", fg="#FFFFFF", activebackground="#005999", state="disabled", command=lambda idx=i: self.submit_answer(idx))
            btn.grid(row=i // 2, column=i % 2, padx=15, pady=10)
            self.option_buttons.append(btn)

    def start_session(self):
        self.participant_id = self.pid_entry.get().strip()
        if not self.participant_id:
            messagebox.showerror("Error", "Please enter a valid Participant ID.")
            return

        self.task_variant = self.task_combo.get()
        self.session_duration_sec = 600 if self.task_variant == "Task 0" else 1200

        self.extract_text.config(text=EXTRACTS.get(self.task_variant, ""))

        self.is_running = True
        self.telemetry_records.clear()
        self.trial_counter = 0
        self.start_time_epoch = time.time()

        self.pid_entry.config(state="disabled")
        self.task_combo.config(state="disabled")
        self.start_btn.config(state="disabled")

        # Single main-thread event loop replacing background threads
        self._main_thread_update_loop()
        self.next_question()

    def _main_thread_update_loop(self):
        """Thread-safe update loop executed entirely on the Tkinter main thread."""
        if not self.is_running:
            return

        elapsed = time.time() - self.start_time_epoch
        mins, secs = divmod(int(elapsed), 60)
        self.timer_label.config(text=f"Elapsed Time: {mins:02d}:{secs:02d}")

        # Check Distractor State
        in_window_1 = (DISTRACTOR_1_START <= elapsed < DISTRACTOR_1_END)
        in_window_2 = (DISTRACTOR_2_START <= elapsed < DISTRACTOR_2_END)

        if (in_window_1 or in_window_2) and self.task_variant in ["Task A", "Task B"]:
            if not self.distractor_active:
                self.distractor_active = True
                self.distractor_label.config(text=" ⚡ ACOUSTIC DISTRACTOR ACTIVE (65 dB)", fg="#FF3333")
                self._start_cafeteria_audio()
        else:
            if self.distractor_active:
                self.distractor_active = False
                self.distractor_label.config(text="Acoustic Distractor: INACTIVE", fg="#6C757D")
                self._stop_cafeteria_audio()

        # Check Session Completion
        if elapsed >= self.session_duration_sec:
            self.finish_session()
            return

        self.root.after(200, self._main_thread_update_loop)

    def _start_cafeteria_audio(self):
        candidate_files = ["cafeteria_noise.wav", "cafeteria_noise.wav.wav"]
        sound_file = next((f for f in candidate_files if os.path.exists(f)), None)

        if sound_file and HAS_WINSOUND:
            try:
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            except Exception as e:
                print(f"[WARNING] Sound error: {e}")

    def _stop_cafeteria_audio(self):
        if HAS_WINSOUND:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    def next_question(self):
        if not self.is_running:
            return

        # Cancel previous pending timeout callback if present
        if self.timeout_job:
            self.root.after_cancel(self.timeout_job)
            self.timeout_job = None

        self.trial_counter += 1
        self.current_item = AncientMathTaskGenerator.generate_item(self.task_variant)
        self.prompt_label.config(text=self.current_item["prompt"])

        for i, option_val in enumerate(self.current_item["options"]):
            self.option_buttons[i].config(text=str(option_val), state="normal", bg="#007ACC")

        self.item_start_time = time.time()
        self.timeout_job = self.root.after(int(QUESTION_TIMEOUT_SEC * 1000), self._check_timeout, self.trial_counter)

    def submit_answer(self, option_index: int):
        if not self.is_running or self.item_start_time == 0.0:
            return

        if self.timeout_job:
            self.root.after_cancel(self.timeout_job)
            self.timeout_job = None

        rt = time.time() - self.item_start_time
        selected_val = self.current_item["options"][option_index]
        correct_val = self.current_item["correct_answer"]
        is_correct = (selected_val == correct_val)

        for btn in self.option_buttons:
            btn.config(state="disabled")

        self._record_telemetry(rt=rt, is_correct=is_correct, omission=False, commission=(not is_correct))
        self.next_question()

    def _check_timeout(self, trial_id: int):
        if self.is_running and self.trial_counter == trial_id:
            for btn in self.option_buttons:
                btn.config(state="disabled")

            self._record_telemetry(rt=QUESTION_TIMEOUT_SEC, is_correct=False, omission=True, commission=False)
            self.next_question()

    def _record_telemetry(self, rt: float, is_correct: bool, omission: bool, commission: bool):
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        self.telemetry_records.append({
            "Participant_ID": self.participant_id,
            "Task_Variant": self.task_variant,
            "Trial_Number": self.trial_counter,
            "Timestamp_ISO": now_iso,
            "Timestamp_Epoch": time.time(),
            "Response_Time_Sec": round(rt, 4),
            "Is_Correct": is_correct,
            "Omission_Error": omission,
            "Commission_Error": commission,
            "Distractor_Active": self.distractor_active
        })

    def finish_session(self):
        self.is_running = False
        self._stop_cafeteria_audio()

        if self.timeout_job:
            self.root.after_cancel(self.timeout_job)
            self.timeout_job = None

        self.pid_entry.config(state="normal")
        self.task_combo.config(state="normal")
        self.start_btn.config(state="normal")

        for btn in self.option_buttons:
            btn.config(state="disabled")

        if not self.telemetry_records:
            return

        df = pd.DataFrame(self.telemetry_records)
        filename = f"CPT_Telemetry_{self.participant_id}_{self.task_variant.replace(' ', '_')}.csv"
        df.to_csv(filename, index=False)

        accuracy = df["Is_Correct"].mean() * 100
        mean_rt = df["Response_Time_Sec"].mean()
        rt_var = df["Response_Time_Sec"].std() if len(df) > 1 else 0.0

        summary_msg = (
            f"Session completed successfully for {self.participant_id}!\n\n"
            f"• Task Variant: {self.task_variant}\n"
            f"• Total Trials Executed: {len(df)}\n"
            f"• Accuracy: {accuracy:.2f}%\n"
            f"• Mean Response Time: {mean_rt:.3f} s\n"
            f"• RT Variability: {rt_var:.3f} s\n\n"
            f"Telemetry saved to '{filename}'"
        )
        messagebox.showinfo("Session Complete", summary_msg)

    def on_close(self):
        """Clean shutdown handler for window close event."""
        self.is_running = False
        self._stop_cafeteria_audio()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CPTTaskApp(root)
    root.mainloop()