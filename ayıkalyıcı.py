import json
import re
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import csv

class QAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ultimate Soru-Cevap Üretici")
        self.geometry("1200x800")
        self.qa_pairs = None
        self.create_widgets()
        self.create_menu()

    # -----------------------------
    # Yardımcı Fonksiyonlar (Metotlar)
    # -----------------------------
    def shorten_text(self, text, max_words):
        """
        Metni, max_words'den fazla kelime içeriyorsa ilk max_words kelimeyi alır ve '...' ekler.
        """
        words = text.split()
        if len(words) > max_words:
            return ' '.join(words[:max_words]) + '...'
        return text

    def is_heading(self, line):
        """
        Bir satırdaki alfabetik karakterlerin tamamı büyükse (Türkçe karakterler dahil),
        bu satırı başlık olarak kabul eder.
        """
        cleaned = re.sub(r'[^A-Za-zÇĞİÖŞÜçğıöşü]', '', line)
        if not cleaned:
            return False
        return cleaned == cleaned.upper()

    def get_word_limits(self):
        """
        UI'den girilen kısa, orta ve uzun cevap kelime limitlerini alır.
        Varsayılan değerler; kısa: 30, orta: 50, uzun: 75.
        """
        try:
            short_limit = int(self.short_limit_entry.get())
        except:
            short_limit = 30
        try:
            medium_limit = int(self.medium_limit_entry.get())
        except:
            medium_limit = 50
        try:
            long_limit = int(self.long_limit_entry.get())
        except:
            long_limit = 75
        if short_limit > medium_limit:
            short_limit = medium_limit
        if medium_limit > long_limit:
            medium_limit = long_limit
        return short_limit, medium_limit, long_limit

    def create_answer_variations(self, answer_text, short_limit, medium_limit, long_limit):
        """
        Verilen cevap metninden üç farklı özet varyant üretir.
        """
        words = answer_text.split()
        if not words:
            return []
        variant1 = self.shorten_text(answer_text, short_limit)
        variant2 = self.shorten_text(answer_text, medium_limit)
        variant3 = self.shorten_text(answer_text, long_limit)
        variants = [variant1, variant2, variant3]
        return list(set(variants))  # Tekrar edenleri kaldır

    def extract_key_sentences(self, paragraph):
        """
        Paragraftan önemli cümleleri çıkarır.
        """
        sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
        key_sentences = []
        for sentence in sentences:
            if len(sentence.split()) >= 10:
                key_sentences.append(sentence.strip())
        return key_sentences

    def generate_question(self, key_sentence):
        """
        Anahtar cümleden doğal bir soru oluşturur.
        """
        parts = key_sentence.split()[:6]
        if not parts:
            return "Bu cümle hakkında ne biliyorsunuz?"
        first_word = parts[0].lower()
        if first_word in ["nasıl", "neden", "ne", "kim", "nerede", "hangi"]:
            return f"{first_word.capitalize()} {' '.join(parts[1:])}?"
        else:
            return f"{' '.join(parts)} hakkında ne biliyorsunuz?"

    def remove_duplicates(self, qa_pairs):
        """
        Tekrarlayan veya çok benzer soruları kaldırır.
        """
        unique_questions = {}
        for pair in qa_pairs:
            question = pair["question"]
            answers = pair["answers"]
            if question not in unique_questions:
                unique_questions[question] = answers
            else:
                unique_questions[question].extend(answers)
        # Her sorudaki tekrar eden cevapları da kaldırıyoruz.
        return [{"question": q, "answers": list(set(a))} for q, a in unique_questions.items()]

    def extract_qa_pairs(self, text, progress_callback=None):
        """
        Metni analiz ederek QA çiftleri üretir.
        """
        paragraphs = re.split(r'\n\s*\n', text)
        total_paras = len(paragraphs) if paragraphs else 1
        qa_pairs = []
        short_limit, medium_limit, long_limit = self.get_word_limits()
        for p_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                if progress_callback:
                    progress_callback((p_idx + 1) / total_paras * 100)
                continue
            lines = para.splitlines()
            first_line = lines[0].strip()
            if self.is_heading(first_line) or (len(first_line.split()) < 10 and first_line.isupper()):
                topic = first_line.title()
                rest = " ".join(lines[1:]).strip()
                if not rest:
                    rest = topic
                qa_pairs.append({
                    "question": f"{topic} hakkında genel bilgi verebilir misiniz?",
                    "answers": self.create_answer_variations(rest, short_limit, medium_limit, long_limit)
                })
            else:
                key_sentences = self.extract_key_sentences(para)
                for key_sentence in key_sentences:
                    qa_pairs.append({
                        "question": self.generate_question(key_sentence),
                        "answers": self.create_answer_variations(key_sentence, short_limit, medium_limit, long_limit)
                    })
            if progress_callback:
                progress_callback((p_idx + 1) / total_paras * 100)
            time.sleep(0.05)  # İşlem süresini simüle ediyor
        qa_pairs = self.remove_duplicates(qa_pairs)
        if not qa_pairs and text:
            qa_pairs.append({
                "question": "Metin hakkında genel bilgi verir misiniz?",
                "answers": self.create_answer_variations(text, short_limit, medium_limit, long_limit)
            })
        return qa_pairs

    # -----------------------------
    # Arayüz Bileşenleri ve Olay Metotları
    # -----------------------------
    def create_widgets(self):
        # Ana çerçeve
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Metin girişi için etiket ve scrolled text kutusu
        input_label = tk.Label(main_frame, text="Metin Girişi:")
        input_label.pack(anchor="w")
        self.text_entry = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=100, height=15)
        self.text_entry.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # İşlem, dosya yükleme, temizleme, önizleme ve kaydetme butonları
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Dosya Yükle", command=self.load_file).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Temizle", command=self.clear_text).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="İşle", command=self.process_text).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Önizleme", command=self.preview_qa_pairs).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Kaydet", command=self.save_file).pack(side=tk.LEFT, padx=5)

        # İlerleme çubuğu ve yüzde etiketi
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=400, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        self.progress_label = tk.Label(progress_frame, text="İlerleme: 0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        # Kelime limiti ayarları
        limits_frame = tk.Frame(main_frame)
        limits_frame.pack(fill=tk.X, pady=5)
        tk.Label(limits_frame, text="Kısa Cevap Kelime Limiti:").pack(side=tk.LEFT)
        self.short_limit_entry = tk.Entry(limits_frame, width=5)
        self.short_limit_entry.insert(0, "30")
        self.short_limit_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(limits_frame, text="Orta Cevap Kelime Limiti:").pack(side=tk.LEFT)
        self.medium_limit_entry = tk.Entry(limits_frame, width=5)
        self.medium_limit_entry.insert(0, "50")
        self.medium_limit_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(limits_frame, text="Uzun Cevap Kelime Limiti:").pack(side=tk.LEFT)
        self.long_limit_entry = tk.Entry(limits_frame, width=5)
        self.long_limit_entry.insert(0, "75")
        self.long_limit_entry.pack(side=tk.LEFT, padx=5)

        # Çıktı formatı seçimi (JSON, TXT, Markdown, HTML, CSV)
        format_frame = tk.Frame(main_frame)
        format_frame.pack(fill=tk.X, pady=5)
        tk.Label(format_frame, text="Çıktı Formatı:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value="json")
        formats = [("JSON", "json"), ("TXT", "txt"), ("Markdown", "md"), ("HTML", "html"), ("CSV", "csv")]
        for text, value in formats:
            tk.Radiobutton(format_frame, text=text, variable=self.output_var, value=value).pack(side=tk.LEFT, padx=5)

    def create_menu(self):
        menubar = tk.Menu(self)
        # Dosya Menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Dosya Yükle", command=self.load_file)
        file_menu.add_command(label="Kaydet", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.quit)
        menubar.add_cascade(label="Dosya", menu=file_menu)

        # Yardım Menüsü
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Hakkında", command=self.show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)

        self.config(menu=menubar)

    def update_progress(self, value):
        self.progress_bar['value'] = value
        self.progress_label.config(text=f"İlerleme: {int(value)}%")
        self.update_idletasks()

    def process_text_thread(self):
        start_time = time.time()
        text = self.text_entry.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Uyarı", "Lütfen metin girin veya dosya yükleyin.")
            return
        self.progress_bar['value'] = 0
        self.progress_label.config(text="İlerleme: 0%")
        self.update_idletasks()
        try:
            qa_pairs = self.extract_qa_pairs(text, progress_callback=self.update_progress)
            self.qa_pairs = qa_pairs
            elapsed = time.time() - start_time
            messagebox.showinfo("Bilgi", f"Metin analizi tamamlandı! Toplam {len(qa_pairs)} QA çifti üretildi.\nSüre: {elapsed:.2f} saniye.")
        except Exception as e:
            messagebox.showerror("Hata", f"Metin işlenirken hata oluştu: {str(e)}")

    def process_text(self):
        threading.Thread(target=self.process_text_thread, daemon=True).start()

    def save_output(self, qa_pairs, output_format):
        """
        Üretilen QA çiftlerini seçilen formatta kaydeder.
        """
        file_types = []
        if output_format == 'json':
            file_types = [('JSON Dosyası', '*.json')]
        elif output_format == 'txt':
            file_types = [('Metin Dosyası', '*.txt')]
        elif output_format == 'md':
            file_types = [('Markdown Dosyası', '*.md')]
        elif output_format == 'html':
            file_types = [('HTML Dosyası', '*.html')]
        elif output_format == 'csv':
            file_types = [('CSV Dosyası', '*.csv')]
        else:
            messagebox.showerror("Hata", "Geçersiz dosya formatı seçildi.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=f'.{output_format}', filetypes=file_types)
        if not file_path:
            return

        try:
            if output_format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(qa_pairs, f, ensure_ascii=False, indent=4)
            elif output_format == 'txt':
                with open(file_path, 'w', encoding='utf-8') as f:
                    for pair in qa_pairs:
                        f.write(f"Soru: {pair['question']}\n")
                        for ans in pair['answers']:
                            f.write(f"- {ans}\n")
                        f.write("\n")
            elif output_format == 'md':
                with open(file_path, 'w', encoding='utf-8') as f:
                    for pair in qa_pairs:
                        f.write(f"### {pair['question']}\n\n")
                        for idx, ans in enumerate(pair['answers'], start=1):
                            f.write(f"{idx}. {ans}\n")
                        f.write("\n")
            elif output_format == 'html':
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n<title>Soru-Cevap</title>\n</head>\n<body>\n")
                    for pair in qa_pairs:
                        f.write(f"<h3>{pair['question']}</h3>\n<ul>\n")
                        for ans in pair['answers']:
                            f.write(f"<li>{ans}</li>\n")
                        f.write("</ul>\n")
                    f.write("</body>\n</html>")
            elif output_format == 'csv':
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Soru", "Cevaplar"])
                    for pair in qa_pairs:
                        writer.writerow([pair['question'], " | ".join(pair['answers'])])
            messagebox.showinfo("Başarı", f"Dosya {file_path} olarak kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilemedi: {str(e)}")

    def save_file(self):
        if self.qa_pairs is None:
            messagebox.showwarning("Uyarı", "Önce metni işlemeniz gerekiyor!")
            return
        self.save_output(self.qa_pairs, self.output_var.get())

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('Metin Dosyaları', '*.txt'),
                                                           ('JSON Dosyaları', '*.json'),
                                                           ('Tüm Dosyalar', '*.*')])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_entry.delete("1.0", "end")
                self.text_entry.insert("end", content)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı: {str(e)}")

    def preview_qa_pairs(self):
        if self.qa_pairs is None:
            messagebox.showwarning("Uyarı", "Önce metni işlemeniz gerekiyor!")
            return
        preview_window = tk.Toplevel(self)
        preview_window.title("QA Çiftleri Önizlemesi")
        preview_window.geometry("800x600")
        preview_text = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD, width=100, height=30)
        preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        preview_content = ""
        for pair in self.qa_pairs:
            preview_content += f"Soru: {pair['question']}\n"
            for ans in pair['answers']:
                preview_content += f"- {ans}\n"
            preview_content += "\n"
        preview_text.insert("end", preview_content)
        preview_text.config(state=tk.DISABLED)

    def clear_text(self):
        if messagebox.askyesno("Onay", "Metni temizlemek istediğinizden emin misiniz?"):
            self.text_entry.delete("1.0", "end")
            self.qa_pairs = None
            self.progress_bar['value'] = 0
            self.progress_label.config(text="İlerleme: 0%")

    def show_about(self):
        messagebox.showinfo("Hakkında", "Ultimate Soru-Cevap Üretici\nSürüm 2.0\nGeliştirici: Koçum\n\nBu uygulama, metin analizi yaparak otomatik QA (Soru-Cevap) çiftleri üretir.\nGelişmiş dosya yükleme, önizleme ve farklı formatlarda kaydetme özellikleri mevcuttur.")

# -----------------------------
# Uygulamanın Çalıştırılması
# -----------------------------
def main():
    app = QAApp()
    app.mainloop()

if __name__ == "__main__":
    main()
