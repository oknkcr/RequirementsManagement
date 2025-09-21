import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, filedialog
import json
import os
from datetime import datetime
try:
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.pagesizes import A4, letter, landscape
    from reportlab.lib.colors import black, white, red
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class RequirementApp:

    # Geçmiş takibi
    def add_to_history(self, action, object_type, object_id, description, details=None):
        """Değişiklik geçmişine kayıt ekle"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": self.current_user,
            "action": action,  # CREATE, MODIFY, DELETE, COMMENT, REVIEW
            "object_type": object_type,  # requirement, group, text
            "object_id": str(object_id),
            "description": description,
            "details": details or {}
        }
        self.history.append(history_entry)
        
        # Son 1000 kayıt tut
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    # Comment sistemi
    def add_comment(self):
        """Seçili objeye yorum ekle"""
        if not hasattr(self, 'right_click_id'):
            return
        
        num = self.right_click_id
        object_key = f"req_{num}"
        
        # Yorum ekleme penceresi
        comment_win = tk.Toplevel(self.root)
        comment_win.title("Yorum Ekle")
        comment_win.geometry("400x300")
        
        tk.Label(comment_win, text=f"Gereksinim: {self.requirements[num]['text']}", 
                font=("Arial", 10, "bold")).pack(pady=10)
        
        tk.Label(comment_win, text="Yorumunuz:").pack(anchor="w", padx=10)
        comment_text = tk.Text(comment_win, width=50, height=10)
        comment_text.pack(padx=10, pady=5)
        
        # Öncelik seçimi
        priority_frame = tk.Frame(comment_win)
        priority_frame.pack(pady=5)
        tk.Label(priority_frame, text="Öncelik:").pack(side="left")
        priority_var = tk.StringVar(value="Normal")
        ttk.Combobox(priority_frame, textvariable=priority_var, 
                    values=["Düşük", "Normal", "Yüksek", "Kritik"], 
                    state="readonly").pack(side="left", padx=5)
        
        def save_comment():
            comment_content = comment_text.get("1.0", "end-1c").strip()
            if not comment_content:
                messagebox.showwarning("Uyarı", "Yorum boş olamaz!")
                return
            
            comment_data = {
                "id": len(self.comments.get(object_key, [])) + 1,
                "author": self.current_user,
                "timestamp": datetime.now().isoformat(),
                "content": comment_content,
                "priority": priority_var.get(),
                "resolved": False
            }
            
            if object_key not in self.comments:
                self.comments[object_key] = []
            self.comments[object_key].append(comment_data)
            
            # Geçmişe kaydet
            self.add_to_history("COMMENT", "requirement", num, 
                              f"Yorum eklendi: {comment_content[:50]}...")
            
            # Gereksinim kutusunu yeniden çiz
            self.canvas.delete(f"req{num}")
            self.draw_requirement(num)
            
            comment_win.destroy()
            messagebox.showinfo("Başarılı", "Yorum eklendi!")
        
        btn_frame = tk.Frame(comment_win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Kaydet", command=save_comment).pack(side="left", padx=5)
        tk.Button(btn_frame, text="İptal", command=comment_win.destroy).pack(side="left", padx=5)

    def show_comments_panel(self):
        """Tüm yorumları gösteren panel"""
        comments_win = tk.Toplevel(self.root)
        comments_win.title("Yorumlar")
        comments_win.geometry("600x500")
        
        # Frame ve scrollbar
        main_frame = tk.Frame(comments_win)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Yorumları listele
        for object_key, comment_list in self.comments.items():
            if not comment_list:
                continue
                
            # Obje başlığı
            obj_type, obj_id = object_key.split("_")
            if obj_type == "req" and int(obj_id) in self.requirements:
                obj_title = self.requirements[int(obj_id)]["text"]
                
                # Obje frame
                obj_frame = tk.LabelFrame(scrollable_frame, text=f"Gereksinim: {obj_title}", 
                                        font=("Arial", 10, "bold"))
                obj_frame.pack(fill="x", pady=5)
                
                for comment in comment_list:
                    comment_frame = tk.Frame(obj_frame, relief="raised", bd=1)
                    comment_frame.pack(fill="x", pady=2, padx=5)
                    
                    # Yorum başlığı
                    header_text = f"{comment['author']} - {comment['timestamp'][:16]} - {comment['priority']}"
                    if comment['resolved']:
                        header_text += " ✅"
                    
                    tk.Label(comment_frame, text=header_text, font=("Arial", 8), 
                           fg="blue").pack(anchor="w")
                    
                    # Yorum içeriği
                    tk.Label(comment_frame, text=comment['content'], 
                           wraplength=500, justify="left").pack(anchor="w", padx=10)
                    
                    # Çözüldü olarak işaretle butonu
                    if not comment['resolved']:
                        tk.Button(comment_frame, text="Çözüldü", 
                                command=lambda c=comment: self.resolve_comment(c, comments_win)).pack(anchor="e")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def resolve_comment(self, comment, parent_win):
        """Yorumu çözüldü olarak işaretle"""
        comment['resolved'] = True
        comment['resolved_by'] = self.current_user
        comment['resolved_date'] = datetime.now().isoformat()
        
        # Pencereyi yenile
        parent_win.destroy()
        self.show_comments_panel()

    # Review sistemi
    def request_review(self):
        """Seçili gereksinim için review iste"""
        if not hasattr(self, 'right_click_id'):
            return
        
        num = self.right_click_id
        object_key = f"req_{num}"
        
        # Review isteği penceresi
        review_win = tk.Toplevel(self.root)
        review_win.title("Review İste")
        review_win.geometry("400x250")
        
        tk.Label(review_win, text=f"Gereksinim: {self.requirements[num]['text']}", 
                font=("Arial", 10, "bold")).pack(pady=10)
        
        tk.Label(review_win, text="Reviewer (virgülle ayırın):").pack(anchor="w", padx=10)
        reviewer_entry = tk.Entry(review_win, width=50)
        reviewer_entry.pack(padx=10, pady=5)
        reviewer_entry.insert(0, "Team Lead, Senior Developer")
        
        tk.Label(review_win, text="Review Notları:").pack(anchor="w", padx=10)
        notes_text = tk.Text(review_win, width=50, height=5)
        notes_text.pack(padx=10, pady=5)
        
        # Deadline
        deadline_frame = tk.Frame(review_win)
        deadline_frame.pack(pady=5)
        tk.Label(deadline_frame, text="Deadline (gün):").pack(side="left")
        deadline_var = tk.StringVar(value="3")
        tk.Entry(deadline_frame, textvariable=deadline_var, width=5).pack(side="left", padx=5)
        
        def save_review_request():
            reviewers = [r.strip() for r in reviewer_entry.get().split(",")]
            notes = notes_text.get("1.0", "end-1c").strip()
            
            try:
                deadline_days = int(deadline_var.get())
                from datetime import timedelta
                deadline_date = (datetime.now() + timedelta(days=deadline_days)).isoformat()
            except ValueError:
                deadline_date = None
            
            review_data = {
                "id": len(self.reviews) + 1,
                "requested_by": self.current_user,
                "requested_date": datetime.now().isoformat(),
                "reviewers": reviewers,
                "notes": notes,
                "deadline": deadline_date,
                "status": "pending",
                "responses": []
            }
            
            self.reviews[object_key] = review_data
            
            # Status'u "In Review" yap
            self.requirements[num]["status"] = "In Review"
            self.requirements[num]["modified_date"] = datetime.now().isoformat()
            
            # Geçmişe kaydet
            self.add_to_history("REVIEW", "requirement", num, 
                              f"Review istendi: {', '.join(reviewers)}")
            
            # Gereksinim kutusunu yeniden çiz
            self.canvas.delete(f"req{num}")
            self.draw_requirement(num)
            
            review_win.destroy()
            messagebox.showinfo("Başarılı", "Review isteği gönderildi!")
        
        btn_frame = tk.Frame(review_win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Gönder", command=save_review_request).pack(side="left", padx=5)
        tk.Button(btn_frame, text="İptal", command=review_win.destroy).pack(side="left", padx=5)

    def show_review_panel(self):
        """Review panelini göster"""
        review_win = tk.Toplevel(self.root)
        review_win.title("Review Paneli")
        review_win.geometry("700x500")
        
        # Notebook (tabs)
        notebook = ttk.Notebook(review_win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Pending Reviews
        pending_frame = tk.Frame(notebook)
        notebook.add(pending_frame, text="Bekleyen Reviews")
        
        # My Reviews
        my_frame = tk.Frame(notebook)
        notebook.add(my_frame, text="Benim Reviews")
        
        # Completed Reviews
        completed_frame = tk.Frame(notebook)
        notebook.add(completed_frame, text="Tamamlanan Reviews")
        
        self.populate_review_tab(pending_frame, "pending")
        self.populate_review_tab(my_frame, "my")
        self.populate_review_tab(completed_frame, "completed")

    def populate_review_tab(self, parent, tab_type):
        """Review tab'ını doldur"""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Reviews'i listele
        for object_key, review_data in self.reviews.items():
            show_review = False
            
            if tab_type == "pending" and review_data["status"] == "pending":
                show_review = True
            elif tab_type == "my" and review_data["requested_by"] == self.current_user:
                show_review = True
            elif tab_type == "completed" and review_data["status"] in ["approved", "rejected"]:
                show_review = True
            
            if not show_review:
                continue
            
            # Review frame
            review_frame = tk.LabelFrame(scrollable_frame, relief="raised", bd=2)
            review_frame.pack(fill="x", pady=5, padx=5)
            
            # Obje bilgisi
            obj_type, obj_id = object_key.split("_")
            if obj_type == "req" and int(obj_id) in self.requirements:
                req_info = self.requirements[int(obj_id)]
                
                tk.Label(review_frame, text=f"Gereksinim: {req_info['text']}", 
                        font=("Arial", 10, "bold")).pack(anchor="w")
                
                info_text = f"İsteyen: {review_data['requested_by']} | Tarih: {review_data['requested_date'][:16]}"
                if review_data['deadline']:
                    info_text += f" | Deadline: {review_data['deadline'][:16]}"
                
                tk.Label(review_frame, text=info_text, font=("Arial", 8)).pack(anchor="w")
                
                if review_data['notes']:
                    tk.Label(review_frame, text=f"Notlar: {review_data['notes']}", 
                           wraplength=600).pack(anchor="w")
                
                # Review butonları
                if tab_type == "pending" and review_data["status"] == "pending":
                    btn_frame = tk.Frame(review_frame)
                    btn_frame.pack(anchor="w", pady=5)
                    
                    tk.Button(btn_frame, text="Onayla", bg="lightgreen",
                            command=lambda oid=int(obj_id): self.approve_review(oid)).pack(side="left", padx=2)
                    tk.Button(btn_frame, text="Reddet", bg="lightcoral",
                            command=lambda oid=int(obj_id): self.reject_review(oid)).pack(side="left", padx=2)
                
                # Status göster
                status_color = {"pending": "orange", "approved": "green", "rejected": "red"}
                tk.Label(review_frame, text=f"Durum: {review_data['status']}", 
                        fg=status_color.get(review_data['status'], "black")).pack(anchor="e")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def approve_review(self, req_id):
        """Review'ı onayla"""
        object_key = f"req_{req_id}"
        if object_key in self.reviews:
            self.reviews[object_key]["status"] = "approved"
            self.reviews[object_key]["approved_by"] = self.current_user
            self.reviews[object_key]["approved_date"] = datetime.now().isoformat()
            
            # Gereksinim status'unu güncelle
            self.requirements[req_id]["status"] = "Approved"
            self.requirements[req_id]["modified_date"] = datetime.now().isoformat()
            
            # Geçmişe kaydet
            self.add_to_history("APPROVE", "requirement", req_id, "Review onaylandı")
            
            # Gereksinim kutusunu yeniden çiz
            self.canvas.delete(f"req{req_id}")
            self.draw_requirement(req_id)
            
            messagebox.showinfo("Başarılı", "Review onaylandı!")

    def reject_review(self, req_id):
        """Review'ı reddet"""
        # Reddetme sebebi sor
        reason = simpledialog.askstring("Reddetme Sebebi", "Neden reddediliyor?")
        if not reason:
            return
        
        object_key = f"req_{req_id}"
        if object_key in self.reviews:
            self.reviews[object_key]["status"] = "rejected"
            self.reviews[object_key]["rejected_by"] = self.current_user
            self.reviews[object_key]["rejected_date"] = datetime.now().isoformat()
            self.reviews[object_key]["rejection_reason"] = reason
            
            # Gereksinim status'unu güncelle
            self.requirements[req_id]["status"] = "Rejected"
            self.requirements[req_id]["modified_date"] = datetime.now().isoformat()
            
            # Geçmişe kaydet
            self.add_to_history("REJECT", "requirement", req_id, f"Review reddedildi: {reason}")
            
            # Gereksinim kutusunu yeniden çiz
            self.canvas.delete(f"req{req_id}")
            self.draw_requirement(req_id)
            
            messagebox.showinfo("Başarılı", "Review reddedildi!")

    def change_status(self):
        """Gereksinim status'unu değiştir"""
        if not hasattr(self, 'right_click_id'):
            return
        
        num = self.right_click_id
        current_status = self.requirements[num].get("status", "Draft")
        
        # Status seçim penceresi
        status_win = tk.Toplevel(self.root)
        status_win.title("Durum Değiştir")
        status_win.geometry("300x200")
        
        tk.Label(status_win, text=f"Gereksinim: {self.requirements[num]['text']}", 
                font=("Arial", 10, "bold")).pack(pady=10)
        
        tk.Label(status_win, text=f"Mevcut Durum: {current_status}").pack()
        
        tk.Label(status_win, text="Yeni Durum:").pack(pady=(10,5))
        status_var = tk.StringVar(value=current_status)
        
        for status in self.status_options:
            tk.Radiobutton(status_win, text=status, variable=status_var, value=status).pack(anchor="w", padx=20)
        
        def save_status():
            new_status = status_var.get()
            if new_status != current_status:
                old_status = self.requirements[num]["status"]
                self.requirements[num]["status"] = new_status
                self.requirements[num]["modified_date"] = datetime.now().isoformat()
                
                # Geçmişe kaydet
                self.add_to_history("MODIFY", "requirement", num, 
                                  f"Durum değiştirildi: {old_status} → {new_status}")
                
                # Gereksinim kutusunu yeniden çiz
                self.canvas.delete(f"req{num}")
                self.draw_requirement(num)
                
                messagebox.showinfo("Başarılı", f"Durum '{new_status}' olarak değiştirildi!")
            
            status_win.destroy()
        
        btn_frame = tk.Frame(status_win)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Kaydet", command=save_status).pack(side="left", padx=5)
        tk.Button(btn_frame, text="İptal", command=status_win.destroy).pack(side="left", padx=5)

    def show_history_panel(self):
        """Değişiklik geçmişi panelini göster"""
        history_win = tk.Toplevel(self.root)
        history_win.title("Değişiklik Geçmişi")
        history_win.geometry("800x600")
        
        # Filtre frame
        filter_frame = tk.Frame(history_win)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(filter_frame, text="Filtre:").pack(side="left")
        
        # Action filtresi
        tk.Label(filter_frame, text="Eylem:").pack(side="left", padx=(20,5))
        action_var = tk.StringVar(value="Tümü")
        action_combo = ttk.Combobox(filter_frame, textvariable=action_var, width=10,
                                   values=["Tümü", "CREATE", "MODIFY", "DELETE", "COMMENT", "REVIEW", "APPROVE", "REJECT"])
        action_combo.pack(side="left", padx=5)
        
        # Kullanıcı filtresi
        tk.Label(filter_frame, text="Kullanıcı:").pack(side="left", padx=(20,5))
        user_var = tk.StringVar(value="Tümü")
        users = ["Tümü"] + list(set([h["user"] for h in self.history]))
        user_combo = ttk.Combobox(filter_frame, textvariable=user_var, width=15, values=users)
        user_combo.pack(side="left", padx=5)
        
        # Yenile butonu
        tk.Button(filter_frame, text="Filtrele", command=lambda: self.refresh_history(history_listbox, action_var.get(), user_var.get())).pack(side="left", padx=10)
        
        # History listbox
        history_frame = tk.Frame(history_win)
        history_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview for better formatting
        columns = ("Zaman", "Kullanıcı", "Eylem", "Obje", "Açıklama")
        history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=20)
        
        # Column headers
        history_tree.heading("Zaman", text="Zaman")
        history_tree.heading("Kullanıcı", text="Kullanıcı")
        history_tree.heading("Eylem", text="Eylem")
        history_tree.heading("Obje", text="Obje")
        history_tree.heading("Açıklama", text="Açıklama")
        
        # Column widths
        history_tree.column("Zaman", width=120)
        history_tree.column("Kullanıcı", width=100)
        history_tree.column("Eylem", width=80)
        history_tree.column("Obje", width=100)
        history_tree.column("Açıklama", width=300)
        
        # Scrollbar
        history_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=history_tree.yview)
        history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        history_tree.pack(side="left", fill="both", expand=True)
        history_scrollbar.pack(side="right", fill="y")
        
        # Store reference for filtering
        history_listbox = history_tree
        
        # İlk yükleme
        self.refresh_history(history_listbox, "Tümü", "Tümü")
        
        # Export butonu
        export_frame = tk.Frame(history_win)
        export_frame.pack(pady=5)
        tk.Button(export_frame, text="Geçmişi Dışa Aktar", command=self.export_history).pack()

    def refresh_history(self, tree_widget, action_filter, user_filter):
        """Geçmiş listesini yenile"""
        # Clear existing items
        for item in tree_widget.get_children():
            tree_widget.delete(item)
        
        # Filter and sort history (newest first)
        filtered_history = []
        for entry in reversed(self.history):
            if action_filter != "Tümü" and entry["action"] != action_filter:
                continue
            if user_filter != "Tümü" and entry["user"] != user_filter:
                continue
            filtered_history.append(entry)
        
        # Add to tree
        for entry in filtered_history:
            timestamp = entry["timestamp"][:19].replace("T", " ")
            object_desc = f"{entry['object_type']} #{entry['object_id']}"
            
            tree_widget.insert("", "end", values=(
                timestamp,
                entry["user"],
                entry["action"],
                object_desc,
                entry["description"]
            ))

    def export_history(self):
        """Geçmişi CSV olarak dışa aktar"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Geçmişi Kaydet"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Zaman', 'Kullanıcı', 'Eylem', 'Obje Türü', 'Obje ID', 'Açıklama', 'Detaylar']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for entry in reversed(self.history):
                        writer.writerow({
                            'Zaman': entry['timestamp'],
                            'Kullanıcı': entry['user'],
                            'Eylem': entry['action'],
                            'Obje Türü': entry['object_type'],
                            'Obje ID': entry['object_id'],
                            'Açıklama': entry['description'],
                            'Detaylar': str(entry.get('details', ''))
                        })
                
                messagebox.showinfo("Başarılı", f"Geçmiş dışa aktarıldı:\n{filename}")
            except Exception as e:
                messagebox.showerror("Hata", f"Dışa aktarma hatası:\n{str(e)}")

    # Kullanıcı yönetimi
    def set_current_user(self):
        """Mevcut kullanıcı adını ayarla"""
        new_user = simpledialog.askstring("Kullanıcı Adı", "Kullanıcı adınızı girin:", 
                                         initialvalue=self.current_user)
        if new_user:
            old_user = self.current_user
            self.current_user = new_user
            self.add_to_history("SYSTEM", "user", "change", f"Kullanıcı değişti: {old_user} → {new_user}")

    # Mevcut edit fonksiyonlarını güncelle (geçmiş kaydı ekle)
    def edit_title(self):
        num = self.right_click_id
        if not num: return
        
        # Katman kilit kontrolü
        layer = self.requirements[num].get("layer", "Requirements")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
        
        old_text = self.requirements[num]["text"]
        new_text = simpledialog.askstring("Başlık Düzenle","Yeni başlık gir:",initialvalue=old_text)
        if new_text and new_text != old_text:
            self.requirements[num]["text"] = new_text
            self.requirements[num]["modified_date"] = datetime.now().isoformat()
            self.canvas.itemconfig(self.requirements[num]["text_id"], text=new_text)
            
            # Geçmişe kaydet
            self.add_to_history("MODIFY", "requirement", num, f"Başlık değişti: '{old_text}' → '{new_text}'")

    def edit_note(self):
        num = self.right_click_id
        if num: 
            # Katman kilit kontrolü
            layer = self.requirements[num].get("layer", "Requirements")
            if self.is_layer_locked(layer):
                messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
                return
            self.open_detail(num)

    def delete_requirement(self):
        num = self.right_click_id
        if not num: return
        
        # Katman kilit kontrolü
        layer = self.requirements[num].get("layer", "Requirements")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
        
        # Onay iste
        req_text = self.requirements[num]["text"]
        if not messagebox.askyesno("Silme Onayı", f"'{req_text}' gereksinimini silmek istediğinizden emin misiniz?"):
            return
        
        # Seçili itemlardan çıkar
        if ("req", num) in self.selected_items:
            self.selected_items.remove(("req", num))
        
        # Canvas objelerini sil
        for t in ["rect","text_id","id_text_id","status_text_id","child_text_id"]:
            if t in self.requirements[num]:
                self.canvas.delete(self.requirements[num][t])
        if "status_text_id" in self.requirements[num]:
            print("Siliniyor:", self.requirements[num]["status_text_id"])
            self.canvas.delete(self.requirements[num]["status_text_id"])        
        
        # Bağlantıları temizle
        if num in self.links: 
            del self.links[num]
        for pid in list(self.links.keys()):
            if num in self.links[pid]:
                self.links[pid].remove(num)
                self.update_child_list(pid)
        
        # Yorumları ve review'ları sil
        object_key = f"req_{num}"
        if object_key in self.comments:
            del self.comments[object_key]
        if object_key in self.reviews:
            del self.reviews[object_key]
        
        # Geçmişe kaydet
        self.add_to_history("DELETE", "requirement", num, f"Gereksinim silindi: {req_text}")
        
        # Gereksinimi sil
        del self.requirements[num]
        self.redraw_links()
        self.update_layer_objects()
        self.update_canvas_visibility()

    # JSON kaydetme/yükleme güncelleme
    def save_data(self):
        data = {
            "requirements": self.requirements,
            "links": self.links,
            "groups": self.groups,
            "text_boxes": self.text_boxes,
            "layers": self.layers,
            "current_layer": self.current_layer,
            "comments": self.comments,
            "reviews": self.reviews,
            "history": self.history,
            "current_user": self.current_user,
            "next_id": self.next_id,
            "next_group_id": self.next_group_id,
            "next_text_id": self.next_text_id,
            "id_prefix": self.id_prefix,
            "zoom_factor": self.zoom_factor
        }
        
        # Canvas objelerini temizle
        for r in data["requirements"].values():
            for k in ["rect","text_id","id_text_id","status_text_id","child_text_id"]:
                r.pop(k,None)
        for g in data["groups"].values():
            for k in ["rect","title","resize_handle"]:
                g.pop(k,None)
        for t in data["text_boxes"].values():
            for k in ["rect","text","resize_handle"]:
                t.pop(k,None)
        
        with open("requirements.json","w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
        messagebox.showinfo("Kaydedildi","Tüm veriler requirements.json dosyasına kaydedildi")

    def load_data(self):
        try:
            with open("requirements.json","r",encoding="utf-8") as f:
                data = json.load(f)
            
            self.requirements = {int(k):v for k,v in data.get("requirements",{}).items()}
            self.links = {int(k):v for k,v in data.get("links",{}).items()}
            self.groups = {int(k):v for k,v in data.get("groups",{}).items()}
            self.text_boxes = {int(k):v for k,v in data.get("text_boxes",{}).items()}
            
            # İşbirliği verilerini yükle
            self.comments = data.get("comments", {})
            self.reviews = data.get("reviews", {})
            self.history = data.get("history", [])
            self.current_user = data.get("current_user", "Kullanıcı")
            
            # Katman verilerini yükle
            if "layers" in data:
                self.layers = data["layers"]
            if "current_layer" in data:
                self.current_layer = data["current_layer"]
                self.layer_var.set(self.current_layer)
            
            self.next_id = data.get("next_id",1)
            self.next_group_id = data.get("next_group_id",1)
            self.next_text_id = data.get("next_text_id",1)
            self.id_prefix = data.get("id_prefix","R")
            
            # Zoom durumunu yükle
            if "zoom_factor" in data:
                self.zoom_factor = data["zoom_factor"]
                self.update_zoom_label()
            
            # Eski veriler için eksik alanları güncelle
            for info in self.requirements.values():
                if "layer" not in info:
                    info["layer"] = "Requirements"
                if "status" not in info:
                    info["status"] = "Draft"
                if "created_by" not in info:
                    info["created_by"] = "Unknown"
                if "created_date" not in info:
                    info["created_date"] = datetime.now().isoformat()
                if "modified_date" not in info:
                    info["modified_date"] = datetime.now().isoformat()
            
            for info in self.groups.values():
                if "layer" not in info:
                    info["layer"] = "Groups"
            for info in self.text_boxes.values():
                if "layer" not in info:
                    info["layer"] = "Notes"
            
            # Combobox'ı güncelle
            self.layer_combo.configure(values=list(self.layers.keys()))
            
            self.canvas.delete("all")
            
            # Önce grupları çiz (arkaplan için)
            for group_id in self.groups:
                self.draw_group(group_id)
            
            # Sonra gereksinimleri çiz
            for num in self.requirements:
                self.draw_requirement(int(num))
            
            # Text box'ları çiz
            for text_id in self.text_boxes:
                self.draw_text_box(text_id)
            
            self.redraw_links()
            self.update_layer_objects()
            self.update_canvas_visibility()
            
            # Yükleme geçmişe kaydedilsin
            self.add_to_history("SYSTEM", "project", "load", "Proje yüklendi")
            
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", str(e))

    # ------------------------------------------------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("Gereksinim Yönetimi")

        # ID prefix ve sıfırlama
        self.id_prefix = "R"
        self.next_id = 1

        # Ana frame yapısı
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True)

        # Menü çubuğu
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        # Dosya menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Kaydet", command=self.save_data, accelerator="Ctrl+S")
        file_menu.add_command(label="Yükle", command=self.load_data, accelerator="Ctrl+O")
        file_menu.add_separator()
        if PDF_AVAILABLE:
            file_menu.add_command(label="PDF Export", command=self.export_to_pdf)
        file_menu.add_command(label="PNG Export", command=self.export_to_png)
        
        # İşbirliği menüsü
        collab_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="İşbirliği", menu=collab_menu)
        collab_menu.add_command(label="Kullanıcı Ayarla", command=self.set_current_user)
        collab_menu.add_command(label="Yorumlar", command=self.show_comments_panel)
        collab_menu.add_command(label="Review Paneli", command=self.show_review_panel)
        collab_menu.add_command(label="Değişiklik Geçmişi", command=self.show_history_panel)
        
        # Görünüm menüsü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Görünüm", menu=view_menu)
        view_menu.add_command(label="Yakınlaştır", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Uzaklaştır", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Zoom Sıfırla", command=self.reset_zoom, accelerator="Ctrl+0")
        
        # Keyboard shortcuts
        root.bind('<Control-s>', lambda e: self.save_data())
        root.bind('<Control-o>', lambda e: self.load_data())
        root.bind('<Control-plus>', lambda e: self.zoom_in())
        root.bind('<Control-minus>', lambda e: self.zoom_out())
        root.bind('<Control-0>', lambda e: self.reset_zoom())

        # Sol panel - Katman kontrolü
        self.layer_frame = tk.Frame(main_frame, width=200, bg="lightgray")
        self.layer_frame.pack(side="left", fill="y")
        self.layer_frame.pack_propagate(False)

        # Canvas frame
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, width=800, height=700, bg="white")
        self.canvas.pack(fill="both", expand=True)

        # Zoom değişkenleri
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        # Katman sistemi
        self.layers = {
            "Background": {"visible": True, "locked": False, "color": "lightgray", "objects": []},
            "Groups": {"visible": True, "locked": False, "color": "blue", "objects": []},
            "Requirements": {"visible": True, "locked": False, "color": "green", "objects": []},
            "Notes": {"visible": True, "locked": False, "color": "orange", "objects": []}
        }
        self.current_layer = "Requirements"

        # Kontrol butonları
        control_frame = tk.Frame(canvas_frame)
        control_frame.pack(fill="x", pady=5)
        
        self.search_entry = tk.Entry(control_frame)
        self.search_entry.pack(side="left", padx=5)
        tk.Button(control_frame, text="Ara (ID)", command=self.search_id).pack(side="left")
        tk.Button(control_frame, text="ID Prefix", command=self.set_prefix).pack(side="left", padx=5)
        tk.Button(control_frame, text="ID Sıfırla", command=self.reset_ids).pack(side="left", padx=5)

        tk.Button(control_frame, text="Yeni Üst", command=lambda: self.create_requirement("ust")).pack(side="left", padx=5)
        tk.Button(control_frame, text="Yeni Alt", command=lambda: self.create_requirement("alt")).pack(side="left", padx=5)
        tk.Button(control_frame, text="Grup Kutusu", command=self.create_group_box).pack(side="left", padx=5)
        tk.Button(control_frame, text="Text Box", command=self.create_text_box).pack(side="left", padx=5)
        
        tk.Button(control_frame, text="Kaydet", command=self.save_data).pack(side="left", padx=5)
        tk.Button(control_frame, text="Yükle", command=self.load_data).pack(side="left", padx=5)
        
        # Export butonları
        if PDF_AVAILABLE:
            tk.Button(control_frame, text="PDF Export", command=self.export_to_pdf).pack(side="left", padx=5)
        tk.Button(control_frame, text="PNG Export", command=self.export_to_png).pack(side="left", padx=5)
        
        # İşbirliği butonları
        tk.Button(control_frame, text="Yorumlar", command=self.show_comments_panel).pack(side="left", padx=5)
        tk.Button(control_frame, text="Review", command=self.show_review_panel).pack(side="left", padx=5)
        tk.Button(control_frame, text="Geçmiş", command=self.show_history_panel).pack(side="left", padx=5)
        
        # Zoom kontrolleri
        tk.Label(control_frame, text="Zoom:").pack(side="left", padx=(20,5))
        tk.Button(control_frame, text="Yakınlaştır (+)", command=self.zoom_in).pack(side="left", padx=2)
        tk.Button(control_frame, text="Uzaklaştır (-)", command=self.zoom_out).pack(side="left", padx=2)
        tk.Button(control_frame, text="Sıfırla (1:1)", command=self.reset_zoom).pack(side="left", padx=2)
        self.zoom_label = tk.Label(control_frame, text="100%")
        self.zoom_label.pack(side="left", padx=5)

        # Katman kontrol paneli
        self.setup_layer_panel()

        # Sağ tık menüleri
        self.req_menu = tk.Menu(root, tearoff=0)
        self.req_menu.add_command(label="Başlığı Düzenle", command=self.edit_title)
        self.req_menu.add_command(label="Notu Düzenle", command=self.edit_note)
        self.req_menu.add_command(label="Renk Değiştir", command=self.change_req_color)
        self.req_menu.add_command(label="Katman Değiştir", command=self.change_req_layer)
        self.req_menu.add_separator()
        self.req_menu.add_command(label="Yorum Ekle", command=self.add_comment)
        self.req_menu.add_command(label="Review İste", command=self.request_review)
        self.req_menu.add_command(label="Durumu Değiştir", command=self.change_status)
        self.req_menu.add_separator()
        self.req_menu.add_command(label="Sil", command=self.delete_requirement)

        self.group_menu = tk.Menu(root, tearoff=0)
        self.group_menu.add_command(label="Grup Adını Düzenle", command=self.edit_group_name)
        self.group_menu.add_command(label="Boyutu Ayarla", command=self.resize_group_manual)
        self.group_menu.add_command(label="Renk Değiştir", command=self.change_group_color)
        self.group_menu.add_command(label="Katman Değiştir", command=self.change_group_layer)
        self.group_menu.add_command(label="Grubu Sil", command=self.delete_group)

        self.text_menu = tk.Menu(root, tearoff=0)
        self.text_menu.add_command(label="Text'i Düzenle", command=self.edit_text_content)
        self.text_menu.add_command(label="Boyutu Ayarla", command=self.resize_text_manual)
        self.text_menu.add_command(label="Font Boyutu", command=self.change_text_font_size)
        self.text_menu.add_command(label="Katman Değiştir", command=self.change_text_layer)
        self.text_menu.add_command(label="Text'i Sil", command=self.delete_text_box)

        # Event bindings
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Control-Button-1>", self.start_selection)
        self.canvas.bind("<Control-B1-Motion>", self.update_selection)
        self.canvas.bind("<Control-ButtonRelease-1>", self.end_selection)

        # Veri yapıları
        self.requirements = {}
        self.links = {}
        self.groups = {}
        self.text_boxes = {}
        self.next_group_id = 1
        self.next_text_id = 1

        # İşbirliği veri yapıları
        self.comments = {}  # object_id -> [comment_list]
        self.reviews = {}   # object_id -> review_info
        self.history = []   # Tüm değişiklik geçmişi
        self.current_user = "Kullanıcı"  # Varsayılan kullanıcı adı
        
        # Status bilgileri
        self.status_options = ["Draft", "In Review", "Approved", "Rejected", "Implemented"]
        self.status_colors = {
            "Draft": "lightgray",
            "In Review": "lightyellow", 
            "Approved": "lightgreen",
            "Rejected": "lightcoral",
            "Implemented": "lightblue"
        }

        # Sürükleme değişkenleri
        self.dragging_id = None
        self.dragging_type = None
        self.offset_x = 0
        self.offset_y = 0

        # Pan değişkenleri
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Selection değişkenleri
        self.selecting = False
        self.selection_start_x = 0
        self.selection_start_y = 0
        self.selection_rect = None
        self.selected_items = set()
        
        # Group drag değişkenleri
        self.group_dragging = False
        self.group_drag_start_x = 0
        self.group_drag_start_y = 0

        # JSON varsa otomatik yükle
        if os.path.exists("requirements.json"):
            self.load_data()

    # --- Katman sistemi ---
    def setup_layer_panel(self):
        # Başlık
        title_label = tk.Label(self.layer_frame, text="KATMANLAR", 
                              font=("Arial", 12, "bold"), bg="lightgray")
        title_label.pack(pady=10)

        # Aktif katman seçici
        tk.Label(self.layer_frame, text="Aktif Katman:", bg="lightgray").pack()
        self.layer_var = tk.StringVar(value=self.current_layer)
        self.layer_combo = ttk.Combobox(self.layer_frame, textvariable=self.layer_var, 
                                       values=list(self.layers.keys()), state="readonly")
        self.layer_combo.pack(pady=5)
        self.layer_combo.bind("<<ComboboxSelected>>", self.on_layer_change)

        # Katman listesi
        self.layer_listbox_frame = tk.Frame(self.layer_frame, bg="lightgray")
        self.layer_listbox_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Katman kontrolleri için scrollable frame
        self.canvas_layers = tk.Canvas(self.layer_listbox_frame, bg="lightgray")
        self.scrollbar = tk.Scrollbar(self.layer_listbox_frame, orient="vertical", command=self.canvas_layers.yview)
        self.scrollable_frame = tk.Frame(self.canvas_layers, bg="lightgray")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_layers.configure(scrollregion=self.canvas_layers.bbox("all"))
        )

        self.canvas_layers.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_layers.configure(yscrollcommand=self.scrollbar.set)

        self.canvas_layers.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.update_layer_panel()

        # Katman butonları
        button_frame = tk.Frame(self.layer_frame, bg="lightgray")
        button_frame.pack(fill="x", padx=5, pady=5)

        tk.Button(button_frame, text="Yeni Katman", command=self.add_new_layer).pack(fill="x", pady=2)
        tk.Button(button_frame, text="Katman Sil", command=self.delete_layer).pack(fill="x", pady=2)

    def update_layer_panel(self):
        # Mevcut widget'ları temizle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for layer_name, layer_data in self.layers.items():
            # Katman frame
            layer_frame = tk.Frame(self.scrollable_frame, bg="white", relief="raised", bd=1)
            layer_frame.pack(fill="x", pady=2)

            # Üst satır - katman adı ve renk
            top_frame = tk.Frame(layer_frame, bg="white")
            top_frame.pack(fill="x")

            # Renk göstergesi
            color_label = tk.Label(top_frame, text="●", fg=layer_data["color"], 
                                 font=("Arial", 16), bg="white")
            color_label.pack(side="left")

            # Katman adı
            name_label = tk.Label(top_frame, text=layer_name, 
                                font=("Arial", 10, "bold"), bg="white")
            name_label.pack(side="left", padx=5)

            # Obje sayısı
            count = len(layer_data["objects"])
            count_label = tk.Label(top_frame, text=f"({count})", 
                                 font=("Arial", 8), bg="white", fg="gray")
            count_label.pack(side="right")

            # Alt satır - kontroller
            control_frame = tk.Frame(layer_frame, bg="white")
            control_frame.pack(fill="x")

            # Görünürlük checkbox
            visible_var = tk.BooleanVar(value=layer_data["visible"])
            visible_cb = tk.Checkbutton(control_frame, text="Görünür", variable=visible_var, 
                                      command=lambda ln=layer_name, var=visible_var: self.toggle_layer_visibility(ln, var),
                                      bg="white")
            visible_cb.pack(side="left")

            # Kilit checkbox
            locked_var = tk.BooleanVar(value=layer_data["locked"])
            locked_cb = tk.Checkbutton(control_frame, text="Kilitli", variable=locked_var,
                                     command=lambda ln=layer_name, var=locked_var: self.toggle_layer_lock(ln, var),
                                     bg="white")
            locked_cb.pack(side="left")

    def on_layer_change(self, event=None):
        self.current_layer = self.layer_var.get()

    def toggle_layer_visibility(self, layer_name, var):
        self.layers[layer_name]["visible"] = var.get()
        self.update_canvas_visibility()

    def toggle_layer_lock(self, layer_name, var):
        self.layers[layer_name]["locked"] = var.get()

    def update_canvas_visibility(self):
        # Tüm objeler için görünürlüğü güncelle
        for num, info in self.requirements.items():
            layer = info.get("layer", "Requirements")
            visible = self.layers[layer]["visible"]
            state = "normal" if visible else "hidden"
            for tag in [f"req{num}"]:
                items = self.canvas.find_withtag(tag)
                for item in items:
                    self.canvas.itemconfig(item, state=state)

        for group_id, info in self.groups.items():
            layer = info.get("layer", "Groups")
            visible = self.layers[layer]["visible"]
            state = "normal" if visible else "hidden"
            for tag in [f"group{group_id}", f"group{group_id}_resize"]:
                items = self.canvas.find_withtag(tag)
                for item in items:
                    self.canvas.itemconfig(item, state=state)

        for text_id, info in self.text_boxes.items():
            layer = info.get("layer", "Notes")
            visible = self.layers[layer]["visible"]
            state = "normal" if visible else "hidden"
            for tag in [f"text{text_id}", f"text{text_id}_resize"]:
                items = self.canvas.find_withtag(tag)
                for item in items:
                    self.canvas.itemconfig(item, state=state)

        self.redraw_links()

    def add_new_layer(self):
        name = simpledialog.askstring("Yeni Katman", "Katman adı:")
        if name and name not in self.layers:
            self.layers[name] = {
                "visible": True, 
                "locked": False, 
                "color": "black", 
                "objects": []
            }
            self.layer_combo.configure(values=list(self.layers.keys()))
            self.update_layer_panel()

    def delete_layer(self):
        if len(self.layers) <= 1:
            messagebox.showwarning("Uyarı", "En az bir katman olmalı!")
            return
        
        layer_name = simpledialog.askstring("Katman Sil", 
                                           f"Silinecek katman adı:\n{list(self.layers.keys())}")
        if layer_name and layer_name in self.layers:
            if len(self.layers[layer_name]["objects"]) > 0:
                if not messagebox.askyesno("Onay", f"'{layer_name}' katmanında objeler var. Silmek istediğinizden emin misiniz?"):
                    return
            
            del self.layers[layer_name]
            self.layer_combo.configure(values=list(self.layers.keys()))
            if self.current_layer == layer_name:
                self.current_layer = list(self.layers.keys())[0]
                self.layer_var.set(self.current_layer)
            self.update_layer_panel()

    def is_layer_locked(self, layer_name):
        return self.layers.get(layer_name, {}).get("locked", False)

    def update_layer_objects(self):
        # Tüm katmanların obje listelerini temizle
        for layer_data in self.layers.values():
            layer_data["objects"] = []

        # Objeleri katmanlarına göre dağıt
        for num, info in self.requirements.items():
            layer = info.get("layer", "Requirements")
            if layer in self.layers:
                self.layers[layer]["objects"].append(("req", num))

        for group_id, info in self.groups.items():
            layer = info.get("layer", "Groups")
            if layer in self.layers:
                self.layers[layer]["objects"].append(("group", group_id))

        for text_id, info in self.text_boxes.items():
            layer = info.get("layer", "Notes")
            if layer in self.layers:
                self.layers[layer]["objects"].append(("text", text_id))

        self.update_layer_panel()

    # Katman değiştirme menü fonksiyonları
    def change_req_layer(self):
        if not hasattr(self, 'right_click_id'):
            return
        
        num = self.right_click_id
        current_layer = self.requirements[num].get("layer", "Requirements")
        
        new_layer = self.select_layer_dialog("Gereksinim Katmanı", current_layer)
        if new_layer:
            self.requirements[num]["layer"] = new_layer
            self.update_layer_objects()
            self.update_canvas_visibility()

    def change_group_layer(self):
        if not hasattr(self, 'right_click_group'):
            return
        
        group_id = self.right_click_group
        current_layer = self.groups[group_id].get("layer", "Groups")
        
        new_layer = self.select_layer_dialog("Grup Katmanı", current_layer)
        if new_layer:
            self.groups[group_id]["layer"] = new_layer
            self.update_layer_objects()
            self.update_canvas_visibility()

    def change_text_layer(self):
        if not hasattr(self, 'right_click_text'):
            return
        
        text_id = self.right_click_text
        current_layer = self.text_boxes[text_id].get("layer", "Notes")
        
        new_layer = self.select_layer_dialog("Text Katmanı", current_layer)
        if new_layer:
            self.text_boxes[text_id]["layer"] = new_layer
            self.update_layer_objects()
            self.update_canvas_visibility()

    def select_layer_dialog(self, title, current_layer):
        layer_win = tk.Toplevel(self.root)
        layer_win.title(title)
        layer_win.geometry("250x300")
        
        selected_layer = tk.StringVar(value=current_layer)
        
        tk.Label(layer_win, text="Katman Seç:").pack(pady=5)
        
        for layer_name in self.layers.keys():
            rb = tk.Radiobutton(layer_win, text=layer_name, variable=selected_layer, 
                              value=layer_name)
            rb.pack(anchor="w", padx=20)
        
        result = [None]
        
        def ok_clicked():
            result[0] = selected_layer.get()
            layer_win.destroy()
        
        def cancel_clicked():
            layer_win.destroy()
        
        btn_frame = tk.Frame(layer_win)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Tamam", command=ok_clicked).pack(side="left", padx=5)
        tk.Button(btn_frame, text="İptal", command=cancel_clicked).pack(side="left", padx=5)
        
        layer_win.wait_window()
        return result[0]

    # --- Zoom işlemleri ---
    def zoom_in(self):
        if self.zoom_factor < self.max_zoom:
            center_x = self.canvas.winfo_width() / 2
            center_y = self.canvas.winfo_height() / 2
            self.zoom_at_point(center_x, center_y, 1.2)

    def zoom_out(self):
        if self.zoom_factor > self.min_zoom:
            center_x = self.canvas.winfo_width() / 2
            center_y = self.canvas.winfo_height() / 2
            self.zoom_at_point(center_x, center_y, 1/1.2)

    def reset_zoom(self):
        scale = 1.0 / self.zoom_factor
        self.canvas.scale("all", 0, 0, scale, scale)
        
        # Pozisyonları güncelle
        for info in self.requirements.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
        
        for info in self.groups.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
            info["size"] = (x1-x0, y1-y0)
        
        for info in self.text_boxes.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
            info["size"] = (x1-x0, y1-y0)
        
        self.zoom_factor = 1.0
        self.update_zoom_label()
        self.redraw_links()

    def zoom_at_point(self, x, y, scale):
        canvas_x = self.canvas.canvasx(x)
        canvas_y = self.canvas.canvasy(y)
        
        self.canvas.scale("all", canvas_x, canvas_y, scale, scale)
        
        self.zoom_factor *= scale
        self.zoom_factor = max(self.min_zoom, min(self.max_zoom, self.zoom_factor))
        
        # Pozisyonları güncelle
        for info in self.requirements.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
        
        for info in self.groups.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
            info["size"] = (x1-x0, y1-y0)
        
        for info in self.text_boxes.values():
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
            info["size"] = (x1-x0, y1-y0)
        
        self.update_zoom_label()
        self.redraw_links()

    def on_mousewheel(self, event):
        if event.state & 0x4:  # Ctrl tuşu basılı
            if hasattr(event, 'delta'):  # Windows
                if event.delta > 0:
                    scale = 1.1
                else:
                    scale = 1/1.1
            else:  # Linux
                if event.num == 4:
                    scale = 1.1
                else:
                    scale = 1/1.1
            
            self.zoom_at_point(event.x, event.y, scale)

    def update_zoom_label(self):
        self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")

    # --- Gereksinim işlemleri ---
    def create_requirement(self, rtype, pos=(100,100)):
        # Katman kilit kontrolü
        if self.is_layer_locked(self.current_layer):
            messagebox.showwarning("Uyarı", f"'{self.current_layer}' katmanı kilitli!")
            return

        num = self.next_id
        self.next_id += 1
        rid = f"{self.id_prefix}{num}"

        info = {
            "id": rid,
            "num": num,
            "type": rtype,
            "pos": pos,
            "text": f"Gereksinim {rid}",
            "note": "",
            "children": [],
            "color": "lightgreen" if rtype == "ust" else "lightblue",
            "layer": self.current_layer,
            "status": "Draft",
            "created_by": self.current_user,
            "created_date": datetime.now().isoformat(),
            "modified_date": datetime.now().isoformat()
        }
        self.requirements[num] = info
        self.draw_requirement(num)
        self.update_layer_objects()
        
        # Geçmişe kaydet
        self.add_to_history("CREATE", "requirement", num, f"Gereksinim {rid} oluşturuldu")

    def draw_requirement(self, num):
        info = self.requirements[num]
        x, y = info["pos"]
        
        # Status'a göre renk belirle
        status = info.get("status", "Draft")
        if status in self.status_colors:
            color = self.status_colors[status]
        else:
            color = info.get("color", "lightgreen" if info["type"]=="ust" else "lightblue")

        rect = self.canvas.create_rectangle(x,y,x+160,y+80, fill=color, tags=f"req{num}")
        title = self.canvas.create_text(x+80,y+10, text=info["text"], tags=f"req{num}", font=("Arial", 9, "bold"))
        id_text = self.canvas.create_text(x+80,y+25, text=f"ID: {info['id']}", tags=f"req{num}", font=("Arial",8))
        status_text = self.canvas.create_text(x+80,y+40, text=f"Status: {status}", tags=f"req{num}", font=("Arial",7))
        child_text = self.canvas.create_text(x+80,y+55, text=f"Alt: {info['children']}", tags=f"req{num}", font=("Arial",7))
        
        # Comment göstergesi
        comment_count = len(self.comments.get(f"req_{num}", []))
        if comment_count > 0:
            comment_indicator = self.canvas.create_text(x+150, y+10, text=f"💬{comment_count}", 
                                                       tags=f"req{num}", font=("Arial",8), fill="blue")
        
        # Review göstergesi
        if f"req_{num}" in self.reviews:
            review_status = self.reviews[f"req_{num}"]["status"]
            if review_status == "pending":
                review_indicator = self.canvas.create_text(x+10, y+10, text="⏳", tags=f"req{num}", font=("Arial",10))
            elif review_status == "approved":
                review_indicator = self.canvas.create_text(x+10, y+10, text="✅", tags=f"req{num}", font=("Arial",10))
            elif review_status == "rejected":
                review_indicator = self.canvas.create_text(x+10, y+10, text="❌", tags=f"req{num}", font=("Arial",10))

        info["rect"] = rect
        info["text_id"] = title
        info["id_text_id"] = id_text
        info["status_text_id"] = status_text
        info["child_text_id"] = child_text

        # Event bindings
        self.canvas.tag_bind(f"req{num}", "<Button-1>", self.on_left_click)
        self.canvas.tag_bind(f"req{num}", "<B1-Motion>", self.on_left_drag)
        self.canvas.tag_bind(f"req{num}", "<ButtonRelease-1>", self.on_left_release)
        self.canvas.tag_bind(id_text, "<Double-Button-1>", lambda e, n=num: self.open_detail(n))

    # --- Grup kutusu işlemleri ---
    def create_group_box(self, pos=(200, 150)):
        # Katman kilit kontrolü
        if self.is_layer_locked(self.current_layer):
            messagebox.showwarning("Uyarı", f"'{self.current_layer}' katmanı kilitli!")
            return

        group_id = self.next_group_id
        self.next_group_id += 1
        
        group_info = {
            "id": group_id,
            "name": f"Grup {group_id}",
            "pos": pos,
            "size": (300, 200),
            "color": "lightyellow",
            "layer": self.current_layer
        }
        
        self.groups[group_id] = group_info
        self.draw_group(group_id)
        self.update_layer_objects()

    def draw_group(self, group_id):
        info = self.groups[group_id]
        x, y = info["pos"]
        w, h = info["size"]
        
        rect = self.canvas.create_rectangle(
            x, y, x+w, y+h, 
            fill=info["color"], outline="gray", width=2,
            tags=f"group{group_id}"
        )
        
        title = self.canvas.create_text(
            x+10, y+10, 
            text=info["name"], 
            anchor="nw", 
            font=("Arial", 10, "bold"),
            tags=f"group{group_id}"
        )
        
        resize_handle = self.canvas.create_rectangle(
            x+w-10, y+h-10, x+w, y+h,
            fill="gray", outline="darkgray",
            tags=f"group{group_id}_resize"
        )
        
        info["rect"] = rect
        info["title"] = title
        info["resize_handle"] = resize_handle
        
        # Event bindings
        self.canvas.tag_bind(f"group{group_id}", "<Button-1>", lambda e, gid=group_id: self.start_group_object_drag(e, gid))
        self.canvas.tag_bind(f"group{group_id}", "<B1-Motion>", self.do_group_object_drag)
        self.canvas.tag_bind(f"group{group_id}", "<ButtonRelease-1>", self.stop_group_object_drag)
        
        # Resize events
        self.canvas.tag_bind(f"group{group_id}_resize", "<Button-1>", lambda e, gid=group_id: self.start_group_resize(e, gid))
        self.canvas.tag_bind(f"group{group_id}_resize", "<B1-Motion>", self.do_group_resize)
        self.canvas.tag_bind(f"group{group_id}_resize", "<ButtonRelease-1>", self.stop_group_resize)
        
        self.canvas.tag_lower(f"group{group_id}")

    def start_group_object_drag(self, event, group_id):
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            return

        self.dragging_id = group_id
        self.dragging_type = "group"
        self.offset_x = self.canvas.canvasx(event.x)
        self.offset_y = self.canvas.canvasy(event.y)

    def do_group_object_drag(self, event):
        if not self.dragging_id or self.dragging_type != "group":
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        dx = canvas_x - self.offset_x
        dy = canvas_y - self.offset_y
        
        self.canvas.move(f"group{self.dragging_id}", dx, dy)
        self.canvas.move(f"group{self.dragging_id}_resize", dx, dy)
        
        info = self.groups[self.dragging_id]
        info["pos"] = (info["pos"][0] + dx, info["pos"][1] + dy)
        
        self.offset_x = canvas_x
        self.offset_y = canvas_y

    def stop_group_object_drag(self, event):
        if self.dragging_type == "group":
            self.dragging_id = None
            self.dragging_type = None

    # Grup resize işlemleri
    def start_group_resize(self, event, group_id):
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            return
            
        self.resizing_group = group_id
        self.resize_start_x = self.canvas.canvasx(event.x)
        self.resize_start_y = self.canvas.canvasy(event.y)

    def do_group_resize(self, event):
        if not hasattr(self, 'resizing_group'):
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        info = self.groups[self.resizing_group]
        x, y = info["pos"]
        
        new_w = max(100, canvas_x - x)
        new_h = max(80, canvas_y - y)
        info["size"] = (new_w, new_h)
        
        self.canvas.delete(f"group{self.resizing_group}")
        self.canvas.delete(f"group{self.resizing_group}_resize")
        self.draw_group(self.resizing_group)

    def stop_group_resize(self, event):
        if hasattr(self, 'resizing_group'):
            delattr(self, 'resizing_group')

    # --- Text box işlemleri ---
    def create_text_box(self, pos=(100, 300)):
        # Katman kilit kontrolü
        if self.is_layer_locked(self.current_layer):
            messagebox.showwarning("Uyarı", f"'{self.current_layer}' katmanı kilitli!")
            return

        text_id = self.next_text_id
        self.next_text_id += 1
        
        text_info = {
            "id": text_id,
            "content": "Yeni Text Box",
            "pos": pos,
            "size": (200, 30),
            "font_size": 10,
            "layer": self.current_layer
        }
        
        self.text_boxes[text_id] = text_info
        self.draw_text_box(text_id)
        self.update_layer_objects()

    def draw_text_box(self, text_id):
        info = self.text_boxes[text_id]
        x, y = info["pos"]
        w, h = info["size"]
        
        rect = self.canvas.create_rectangle(
            x, y, x+w, y+h,
            fill="white", outline="lightgray", width=1,
            tags=f"text{text_id}"
        )
        
        text = self.canvas.create_text(
            x+5, y+h//2,
            text=info["content"],
            anchor="w",
            font=("Arial", info["font_size"]),
            tags=f"text{text_id}"
        )
        
        resize_handle = self.canvas.create_rectangle(
            x+w-8, y+h-8, x+w, y+h,
            fill="lightgray", outline="gray",
            tags=f"text{text_id}_resize"
        )
        
        info["rect"] = rect
        info["text"] = text
        info["resize_handle"] = resize_handle
        
        # Event bindings
        self.canvas.tag_bind(f"text{text_id}", "<Button-1>", lambda e, tid=text_id: self.start_text_drag(e, tid))
        self.canvas.tag_bind(f"text{text_id}", "<B1-Motion>", self.do_text_drag)
        self.canvas.tag_bind(f"text{text_id}", "<ButtonRelease-1>", self.stop_text_drag)
        
        # Resize events
        self.canvas.tag_bind(f"text{text_id}_resize", "<Button-1>", lambda e, tid=text_id: self.start_text_resize(e, tid))
        self.canvas.tag_bind(f"text{text_id}_resize", "<B1-Motion>", self.do_text_resize)
        self.canvas.tag_bind(f"text{text_id}_resize", "<ButtonRelease-1>", self.stop_text_resize)

    def start_text_drag(self, event, text_id):
        # Katman kilit kontrolü
        layer = self.text_boxes[text_id].get("layer", "Notes")
        if self.is_layer_locked(layer):
            return

        self.dragging_id = text_id
        self.dragging_type = "text"
        self.offset_x = self.canvas.canvasx(event.x)
        self.offset_y = self.canvas.canvasy(event.y)

    def do_text_drag(self, event):
        if not self.dragging_id or self.dragging_type != "text":
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        dx = canvas_x - self.offset_x
        dy = canvas_y - self.offset_y
        
        self.canvas.move(f"text{self.dragging_id}", dx, dy)
        self.canvas.move(f"text{self.dragging_id}_resize", dx, dy)
        
        info = self.text_boxes[self.dragging_id]
        info["pos"] = (info["pos"][0] + dx, info["pos"][1] + dy)
        
        self.offset_x = canvas_x
        self.offset_y = canvas_y

    def stop_text_drag(self, event):
        if self.dragging_type == "text":
            self.dragging_id = None
            self.dragging_type = None

    # Text box resize işlemleri
    def start_text_resize(self, event, text_id):
        # Katman kilit kontrolü
        layer = self.text_boxes[text_id].get("layer", "Notes")
        if self.is_layer_locked(layer):
            return
            
        self.resizing_text = text_id
        self.resize_start_x = self.canvas.canvasx(event.x)
        self.resize_start_y = self.canvas.canvasy(event.y)

    def do_text_resize(self, event):
        if not hasattr(self, 'resizing_text'):
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        info = self.text_boxes[self.resizing_text]
        x, y = info["pos"]
        
        new_w = max(50, canvas_x - x)
        new_h = max(20, canvas_y - y)
        info["size"] = (new_w, new_h)
        
        self.canvas.delete(f"text{self.resizing_text}")
        self.canvas.delete(f"text{self.resizing_text}_resize")
        self.draw_text_box(self.resizing_text)

    def stop_text_resize(self, event):
        if hasattr(self, 'resizing_text'):
            delattr(self, 'resizing_text')

    # --- Selection işlemleri ---
    def start_selection(self, event):
        self.selecting = True
        self.selection_start_x = event.x
        self.selection_start_y = event.y
        self.clear_selection()

    def update_selection(self, event):
        if not self.selecting:
            return
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        
        x1, y1 = self.selection_start_x, self.selection_start_y
        x2, y2 = event.x, event.y
        
        self.selection_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="blue", dash=(5, 5), tags="selection"
        )

    def end_selection(self, event):
        if not self.selecting:
            return
        
        self.selecting = False
        
        x1 = min(self.selection_start_x, event.x)
        y1 = min(self.selection_start_y, event.y)
        x2 = max(self.selection_start_x, event.x)
        y2 = max(self.selection_start_y, event.y)
        
        canvas_x1 = self.canvas.canvasx(x1)
        canvas_y1 = self.canvas.canvasy(y1)
        canvas_x2 = self.canvas.canvasx(x2)
        canvas_y2 = self.canvas.canvasy(y2)
        
        for num, info in self.requirements.items():
            # Katman görünürlük kontrolü
            layer = info.get("layer", "Requirements")
            if not self.layers[layer]["visible"]:
                continue
                
            rect_coords = self.canvas.coords(info["rect"])
            if len(rect_coords) >= 4:
                rx1, ry1, rx2, ry2 = rect_coords
                if not (rx2 < canvas_x1 or rx1 > canvas_x2 or ry2 < canvas_y1 or ry1 > canvas_y2):
                    self.selected_items.add(("req", num))
                    self.highlight_selected_req(num)
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None

    def clear_selection(self):
        for item_type, item_id in self.selected_items:
            if item_type == "req" and item_id in self.requirements:
                self.canvas.itemconfig(self.requirements[item_id]["rect"], outline="black", width=1)
        self.selected_items.clear()

    def highlight_selected_req(self, num):
        self.canvas.itemconfig(self.requirements[num]["rect"], outline="blue", width=2)

    # --- Multi selection drag işlemleri ---
    def start_multi_selection_drag(self, event):
        if self.selected_items:
            self.group_dragging = True
            self.group_drag_start_x = event.x
            self.group_drag_start_y = event.y

    def do_multi_selection_drag(self, event):
        if not self.group_dragging:
            return
        
        dx = self.canvas.canvasx(event.x) - self.canvas.canvasx(self.group_drag_start_x)
        dy = self.canvas.canvasy(event.y) - self.canvas.canvasy(self.group_drag_start_y)
        
        for item_type, item_id in self.selected_items:
            if item_type == "req" and item_id in self.requirements:
                # Katman kilit kontrolü
                layer = self.requirements[item_id].get("layer", "Requirements")
                if self.is_layer_locked(layer):
                    continue
                    
                self.canvas.move(f"req{item_id}", dx, dy)
                x0, y0, x1, y1 = self.canvas.coords(self.requirements[item_id]["rect"])
                self.requirements[item_id]["pos"] = (x0, y0)
        
        self.group_drag_start_x = event.x
        self.group_drag_start_y = event.y
        self.redraw_links()

    def stop_multi_selection_drag(self, event):
        self.group_dragging = False

    # --- Pan işlemleri ---
    def on_right_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Gereksinim kontrolü
        clicked_req = self.get_requirement_at(canvas_x, canvas_y)
        if clicked_req:
            self.right_click_id = clicked_req
            self.req_menu.post(event.x_root, event.y_root)
            return
        
        # Grup kontrolü
        clicked_group = self.get_group_at(canvas_x, canvas_y)
        if clicked_group:
            self.right_click_group = clicked_group
            self.group_menu.post(event.x_root, event.y_root)
            return
        
        # Text box kontrolü
        clicked_text = self.get_text_at(canvas_x, canvas_y)
        if clicked_text:
            self.right_click_text = clicked_text
            self.text_menu.post(event.x_root, event.y_root)
            return
        
        # Boş alanda sağ tık - pan başlat
        self.start_pan(event)

    def get_group_at(self, x, y):
        for group_id, info in self.groups.items():
            layer = info.get("layer", "Groups")
            if not self.layers[layer]["visible"]:
                continue
            gx, gy = info["pos"]
            gw, gh = info["size"]
            if gx < x < gx+gw and gy < y < gy+gh:
                return group_id
        return None

    def get_text_at(self, x, y):
        for text_id, info in self.text_boxes.items():
            layer = info.get("layer", "Notes")
            if not self.layers[layer]["visible"]:
                continue
            tx, ty = info["pos"]
            tw, th = info["size"]
            if tx < x < tx+tw and ty < y < ty+th:
                return text_id
        return None

    def on_right_release(self, event):
        if self.panning:
            self.stop_pan(event)

    def start_pan(self, event):
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.config(cursor="fleur")

    def do_pan(self, event):
        if not self.panning:
            return
        
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        # Tüm objeleri hareket ettir
        for num, info in self.requirements.items():
            self.canvas.move(f"req{num}", dx, dy)
            x0, y0, x1, y1 = self.canvas.coords(info["rect"])
            info["pos"] = (x0, y0)
        
        for group_id, info in self.groups.items():
            self.canvas.move(f"group{group_id}", dx, dy)
            self.canvas.move(f"group{group_id}_resize", dx, dy)
            info["pos"] = (info["pos"][0] + dx, info["pos"][1] + dy)
        
        for text_id, info in self.text_boxes.items():
            self.canvas.move(f"text{text_id}", dx, dy)
            self.canvas.move(f"text{text_id}_resize", dx, dy)
            info["pos"] = (info["pos"][0] + dx, info["pos"][1] + dy)
        
        self.redraw_links()
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def stop_pan(self, event):
        if self.panning:
            self.panning = False
            self.canvas.unbind("<B3-Motion>")
            self.canvas.config(cursor="")

    # --- Sol tık işlemleri ---
    def on_left_click(self, event):
        item = self.canvas.find_withtag("current")[0]
        clicked_num = None
        for tag in self.canvas.gettags(item):
            if tag.startswith("req"):
                clicked_num = int(tag.replace("req",""))
                break
        
        # Katman kilit kontrolü
        if clicked_num:
            layer = self.requirements[clicked_num].get("layer", "Requirements")
            if self.is_layer_locked(layer):
                return
        
        if event.state & 0x4:  # Ctrl basılı - seçim toggle
            if ("req", clicked_num) in self.selected_items:
                self.selected_items.remove(("req", clicked_num))
                self.canvas.itemconfig(self.requirements[clicked_num]["rect"], outline="black", width=1)
            else:
                self.selected_items.add(("req", clicked_num))
                self.highlight_selected_req(clicked_num)
        else:
            selected_reqs = [item_id for item_type, item_id in self.selected_items if item_type == "req"]
            if clicked_num in selected_reqs:
                self.start_multi_selection_drag(event)
            else:
                self.clear_selection()
                self.start_drag(event, clicked_num)

    def on_left_drag(self, event):
        if self.group_dragging:
            self.do_multi_selection_drag(event)
        elif self.dragging_id and self.dragging_type == "req":
            self.do_drag(event)

    def on_left_release(self, event):
        if self.group_dragging:
            self.stop_multi_selection_drag(event)
        elif self.dragging_id and self.dragging_type == "req":
            self.stop_drag(event)

    # --- Sürükle-bırak (tek item) ---
    def start_drag(self, event, clicked_num):
        self.dragging_id = clicked_num
        self.dragging_type = "req"
        self.offset_x = self.canvas.canvasx(event.x)
        self.offset_y = self.canvas.canvasy(event.y)

    def do_drag(self, event):
        if not self.dragging_id or self.dragging_type != "req": 
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        dx = canvas_x - self.offset_x
        dy = canvas_y - self.offset_y
        
        self.canvas.move(f"req{self.dragging_id}", dx, dy)
        x0,y0,x1,y1 = self.canvas.coords(self.requirements[self.dragging_id]["rect"])
        self.requirements[self.dragging_id]["pos"]=(x0,y0)
        self.offset_x = canvas_x
        self.offset_y = canvas_y
        self.redraw_links()

    def stop_drag(self, event):
        if not self.dragging_id or self.dragging_type != "req": 
            return
        
        dragged_id = self.dragging_id
        self.dragging_id = None
        self.dragging_type = None
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        for num, info in self.requirements.items():
            if num==dragged_id: continue
            x0,y0,x1,y1 = self.canvas.coords(info["rect"])
            if x0<canvas_x<x1 and y0<canvas_y<y1:
                if self.requirements[dragged_id]["type"]=="alt" and info["type"]=="ust":
                    if dragged_id not in info["children"]:
                        info["children"].append(dragged_id)
                        self.links.setdefault(num,[]).append(dragged_id)
                        self.update_child_list(num)
                        self.redraw_links()

    def update_child_list(self,num):
        info = self.requirements[num]
        self.canvas.itemconfig(info["child_text_id"], text=f"Alt: {info['children']}")

    def redraw_links(self):
        self.canvas.delete("link")
        for parent, children in self.links.items():
            if parent not in self.requirements:
                continue
            
            # Katman görünürlük kontrolü
            parent_layer = self.requirements[parent].get("layer", "Requirements")
            if not self.layers[parent_layer]["visible"]:
                continue
                
            coords = self.canvas.coords(self.requirements[parent]["rect"])
            if len(coords) < 4:
                continue
            x0,y0,x1,y1 = coords
            px,py = (x0+x1)/2,y1
            for child in children:
                if child not in self.requirements:
                    continue
                
                # Katman görünürlük kontrolü
                child_layer = self.requirements[child].get("layer", "Requirements")
                if not self.layers[child_layer]["visible"]:
                    continue
                    
                child_coords = self.canvas.coords(self.requirements[child]["rect"])
                if len(child_coords) < 4:
                    continue
                cx0,cy0,cx1,cy1 = child_coords
                cx,cy = (cx0+cx1)/2,cy0
                self.canvas.create_line(px,py,cx,cy, arrow="last", fill="red", tags="link")

    # --- Detaylar ---
    def open_detail(self,num):
        self.highlight_only(num)
        win = tk.Toplevel(self.root)
        win.title(f"{self.requirements[num]['id']} Detay")
        tk.Label(win, text=f"ID: {self.requirements[num]['id']}").pack()
        text_box = tk.Text(win,width=40,height=10)
        text_box.pack()
        text_box.insert("1.0", self.requirements[num]["note"])
        def save_note():
            self.requirements[num]["note"]=text_box.get("1.0","end-1c")
            win.destroy()
        tk.Button(win,text="Kaydet",command=save_note).pack()

    def edit_title(self):
        num = self.right_click_id
        if not num: return
        
        # Katman kilit kontrolü
        layer = self.requirements[num].get("layer", "Requirements")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        new_text = simpledialog.askstring("Başlık Düzenle","Yeni başlık gir:",initialvalue=self.requirements[num]["text"])
        if new_text:
            self.requirements[num]["text"]=new_text
            self.canvas.itemconfig(self.requirements[num]["text_id"], text=new_text)

    def edit_note(self):
        num = self.right_click_id
        if num: 
            # Katman kilit kontrolü
            layer = self.requirements[num].get("layer", "Requirements")
            if self.is_layer_locked(layer):
                messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
                return
            self.open_detail(num)

    def delete_requirement(self):
        num = self.right_click_id
        if not num: return
        
        # Katman kilit kontrolü
        layer = self.requirements[num].get("layer", "Requirements")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
        
        # Seçili itemlardan çıkar
        if ("req", num) in self.selected_items:
            self.selected_items.remove(("req", num))
        
        for t in ["rect","text_id","id_text_id","child_text_id"]:
            if t in self.requirements[num]:
                self.canvas.delete(self.requirements[num][t])
        if num in self.links: del self.links[num]
        for pid in list(self.links.keys()):
            if num in self.links[pid]:
                self.links[pid].remove(num)
                self.update_child_list(pid)
        del self.requirements[num]
        self.redraw_links()
        self.update_layer_objects()

    # --- Renk ve boyut değiştirme menü fonksiyonları ---
    def change_req_color(self):
        if not hasattr(self, 'right_click_id'):
            return
        
        num = self.right_click_id
        # Katman kilit kontrolü
        layer = self.requirements[num].get("layer", "Requirements")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        colors = ["lightgreen", "lightblue", "lightcoral", "lightyellow", 
                 "lightpink", "lightgray", "lightcyan", "wheat", "lavender"]
        
        color_win = tk.Toplevel(self.root)
        color_win.title("Renk Seç")
        color_win.geometry("300x200")
        
        selected_color = tk.StringVar(value=self.requirements[num].get("color", "lightblue"))
        
        for i, color in enumerate(colors):
            row, col = divmod(i, 3)
            btn = tk.Radiobutton(color_win, text=color, variable=selected_color, 
                               value=color, bg=color, width=12)
            btn.grid(row=row, column=col, padx=5, pady=5)
        
        def apply_color():
            new_color = selected_color.get()
            self.requirements[num]["color"] = new_color
            self.canvas.itemconfig(self.requirements[num]["rect"], fill=new_color)
            color_win.destroy()
        
        tk.Button(color_win, text="Uygula", command=apply_color).grid(row=3, column=1, pady=10)

    def change_group_color(self):
        if not hasattr(self, 'right_click_group'):
            return
        
        group_id = self.right_click_group
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        colors = ["lightyellow", "lightblue", "lightgreen", "lightcoral", 
                 "lightpink", "lightgray", "lightcyan", "wheat", "lavender"]
        
        color_win = tk.Toplevel(self.root)
        color_win.title("Grup Rengi Seç")
        color_win.geometry("300x200")
        
        selected_color = tk.StringVar(value=self.groups[group_id]["color"])
        
        for i, color in enumerate(colors):
            row, col = divmod(i, 3)
            btn = tk.Radiobutton(color_win, text=color, variable=selected_color, 
                               value=color, bg=color, width=12)
            btn.grid(row=row, column=col, padx=5, pady=5)
        
        def apply_color():
            new_color = selected_color.get()
            self.groups[group_id]["color"] = new_color
            self.canvas.itemconfig(self.groups[group_id]["rect"], fill=new_color)
            color_win.destroy()
        
        tk.Button(color_win, text="Uygula", command=apply_color).grid(row=3, column=1, pady=10)

    def resize_group_manual(self):
        if not hasattr(self, 'right_click_group'):
            return
        
        group_id = self.right_click_group
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        current_size = self.groups[group_id]["size"]
        
        size_win = tk.Toplevel(self.root)
        size_win.title("Grup Boyutu")
        size_win.geometry("200x150")
        
        tk.Label(size_win, text="Genişlik:").pack()
        width_var = tk.StringVar(value=str(int(current_size[0])))
        width_entry = tk.Entry(size_win, textvariable=width_var)
        width_entry.pack(pady=5)
        
        tk.Label(size_win, text="Yükseklik:").pack()
        height_var = tk.StringVar(value=str(int(current_size[1])))
        height_entry = tk.Entry(size_win, textvariable=height_var)
        height_entry.pack(pady=5)
        
        def apply_size():
            try:
                new_w = max(100, int(width_var.get()))
                new_h = max(80, int(height_var.get()))
                self.groups[group_id]["size"] = (new_w, new_h)
                
                self.canvas.delete(f"group{group_id}")
                self.canvas.delete(f"group{group_id}_resize")
                self.draw_group(group_id)
                size_win.destroy()
            except ValueError:
                messagebox.showerror("Hata", "Geçerli sayı girin!")
        
        tk.Button(size_win, text="Uygula", command=apply_size).pack(pady=10)

    def resize_text_manual(self):
        if not hasattr(self, 'right_click_text'):
            return
        
        text_id = self.right_click_text
            
        current_size = self.text_boxes[text_id]["size"]
        
        size_win = tk.Toplevel(self.root)
        size_win.title("Text Box Boyutu")
        size_win.geometry("200x150")
        
        tk.Label(size_win, text="Genişlik:").pack()
        width_var = tk.StringVar(value=str(int(current_size[0])))
        width_entry = tk.Entry(size_win, textvariable=width_var)
        width_entry.pack(pady=5)
        
        tk.Label(size_win, text="Yükseklik:").pack()
        height_var = tk.StringVar(value=str(int(current_size[1])))
        height_entry = tk.Entry(size_win, textvariable=height_var)
        height_entry.pack(pady=5)
        
        def apply_size():
            try:
                new_w = max(50, int(width_var.get()))
                new_h = max(20, int(height_var.get()))
                self.text_boxes[text_id]["size"] = (new_w, new_h)
                
                self.canvas.delete(f"text{text_id}")
                self.canvas.delete(f"text{text_id}_resize")
                self.draw_text_box(text_id)
                size_win.destroy()
            except ValueError:
                messagebox.showerror("Hata", "Geçerli sayı girin!")
        
        tk.Button(size_win, text="Uygula", command=apply_size).pack(pady=10)

    def change_text_font_size(self):
        if not hasattr(self, 'right_click_text'):
            return
        
        text_id = self.right_click_text
        # Katman kilit kontrolü
        layer = self.text_boxes[text_id].get("layer", "Notes")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        current_size = self.text_boxes[text_id]["font_size"]
        
        new_size = simpledialog.askinteger("Font Boyutu", 
                                         "Yeni font boyutu (6-24):", 
                                         initialvalue=current_size, 
                                         minvalue=6, maxvalue=24)
        
        if new_size:
            self.text_boxes[text_id]["font_size"] = new_size
            self.canvas.itemconfig(self.text_boxes[text_id]["text"], 
                                 font=("Arial", new_size))

    def edit_group_name(self):
        if not hasattr(self, 'right_click_group'):
            return
        
        group_id = self.right_click_group
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        current_name = self.groups[group_id]["name"]
        new_name = simpledialog.askstring("Grup Adı", "Yeni grup adı:", initialvalue=current_name)
        
        if new_name:
            self.groups[group_id]["name"] = new_name
            self.canvas.itemconfig(self.groups[group_id]["title"], text=new_name)

    def delete_group(self):
        if not hasattr(self, 'right_click_group'):
            return
        
        group_id = self.right_click_group
        # Katman kilit kontrolü
        layer = self.groups[group_id].get("layer", "Groups")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        self.canvas.delete(f"group{group_id}")
        self.canvas.delete(f"group{group_id}_resize")
        del self.groups[group_id]
        self.update_layer_objects()

    def edit_text_content(self):
        if not hasattr(self, 'right_click_text'):
            return
        
        text_id = self.right_click_text
        # Katman kilit kontrolü
        layer = self.text_boxes[text_id].get("layer", "Notes")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        current_content = self.text_boxes[text_id]["content"]
        new_content = simpledialog.askstring("Text İçeriği", "Yeni içerik:", initialvalue=current_content)
        
        if new_content:
            self.text_boxes[text_id]["content"] = new_content
            self.canvas.itemconfig(self.text_boxes[text_id]["text"], text=new_content)

    def delete_text_box(self):
        if not hasattr(self, 'right_click_text'):
            return
        
        text_id = self.right_click_text
        # Katman kilit kontrolü
        layer = self.text_boxes[text_id].get("layer", "Notes")
        if self.is_layer_locked(layer):
            messagebox.showwarning("Uyarı", f"'{layer}' katmanı kilitli!")
            return
            
        self.canvas.delete(f"text{text_id}")
        self.canvas.delete(f"text{text_id}_resize")
        del self.text_boxes[text_id]
        self.update_layer_objects()

    # --- Arama ve highlight ---
    def highlight_only(self,num):
        for r in self.requirements.values():
            self.canvas.itemconfig(r["rect"], outline="black", width=1)
        self.canvas.itemconfig(self.requirements[num]["rect"], outline="red", width=3)

    def search_id(self):
        search_text = self.search_entry.get().strip()
        found = None
        for num, info in self.requirements.items():
            if info["id"] == search_text:
                found = num
                break
        if not found:
            messagebox.showinfo("Bulunamadı", f"ID '{search_text}' yok")
            return
        self.highlight_only(found)

    # --- ID Prefix ve sıfırlama ---
    def set_prefix(self):
        new_prefix = simpledialog.askstring("ID Prefix","Yeni ID prefix gir:", initialvalue=self.id_prefix)
        if new_prefix:
            self.id_prefix = new_prefix

    def reset_ids(self):
        self.next_id = 1
        for num, info in self.requirements.items():
            rid = f"{self.id_prefix}{self.next_id}"
            info["id"] = rid
            info["text"] = f"Gereksinim {rid}"
            self.canvas.itemconfig(info["text_id"], text=info["text"])
            self.canvas.itemconfig(info["id_text_id"], text=f"ID: {rid}")
            self.next_id += 1

    # --- JSON ---
    def save_data(self):
        data = {
            "requirements": self.requirements,
            "links": self.links,
            "groups": self.groups,
            "text_boxes": self.text_boxes,
            "layers": self.layers,
            "current_layer": self.current_layer,
            "next_id": self.next_id,
            "next_group_id": self.next_group_id,
            "next_text_id": self.next_text_id,
            "id_prefix": self.id_prefix,
            "zoom_factor": self.zoom_factor
        }
        
        # Canvas objelerini temizle
        for r in data["requirements"].values():
            for k in ["rect","text_id","id_text_id","child_text_id"]:
                r.pop(k,None)
        for g in data["groups"].values():
            for k in ["rect","title","resize_handle"]:
                g.pop(k,None)
        for t in data["text_boxes"].values():
            for k in ["rect","text","resize_handle"]:
                t.pop(k,None)
        
        with open("requirements.json","w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
        messagebox.showinfo("Kaydedildi","requirements.json kaydedildi")

    def load_data(self):
        try:
            with open("requirements.json","r",encoding="utf-8") as f:
                data = json.load(f)
            
            self.requirements = {int(k):v for k,v in data.get("requirements",{}).items()}
            self.links = {int(k):v for k,v in data.get("links",{}).items()}
            self.groups = {int(k):v for k,v in data.get("groups",{}).items()}
            self.text_boxes = {int(k):v for k,v in data.get("text_boxes",{}).items()}
            
            # Katman verilerini yükle
            if "layers" in data:
                self.layers = data["layers"]
            if "current_layer" in data:
                self.current_layer = data["current_layer"]
                self.layer_var.set(self.current_layer)
            
            self.next_id = data.get("next_id",1)
            self.next_group_id = data.get("next_group_id",1)
            self.next_text_id = data.get("next_text_id",1)
            self.id_prefix = data.get("id_prefix","R")
            
            # Zoom durumunu yükle
            if "zoom_factor" in data:
                self.zoom_factor = data["zoom_factor"]
                self.update_zoom_label()
            
            # Eski veriler için layer bilgisini güncelle
            for info in self.requirements.values():
                if "layer" not in info:
                    info["layer"] = "Requirements"
            for info in self.groups.values():
                if "layer" not in info:
                    info["layer"] = "Groups"
            for info in self.text_boxes.values():
                if "layer" not in info:
                    info["layer"] = "Notes"
            
            # Combobox'ı güncelle
            self.layer_combo.configure(values=list(self.layers.keys()))
            
            self.canvas.delete("all")
            
            # Önce grupları çiz (arkaplan için)
            for group_id in self.groups:
                self.draw_group(group_id)
            
            # Sonra gereksinimleri çiz
            for num in self.requirements:
                self.draw_requirement(int(num))
            
            # Text box'ları çiz
            for text_id in self.text_boxes:
                self.draw_text_box(text_id)
            
            self.redraw_links()
            self.update_layer_objects()
            self.update_canvas_visibility()
            
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", str(e))

    def get_requirement_at(self,x,y):
        for num, info in self.requirements.items():
            layer = info.get("layer", "Requirements")
            if not self.layers[layer]["visible"]:
                continue
            rx, ry = info["pos"]
            if rx < x < rx+160 and ry < y < ry+60:
                return num
        return None

    def get_item_at(self,x,y):
        items = self.canvas.find_overlapping(x,y,x,y)
        for it in items:
            for tag in self.canvas.gettags(it):
                if tag.startswith("req"):
                    return int(tag.replace("req",""))
        return None

    # --- Export işlemleri ---
    def export_to_pdf(self):
        if not PDF_AVAILABLE:
            messagebox.showerror("Hata", "PDF export için reportlab kütüphanesi gerekli!\npip install reportlab")
            return
        
        # Dosya kaydetme penceresi
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="PDF olarak kaydet"
        )
        
        if not filename:
            return
        
        self.create_pdf(filename)

    def create_pdf(self, filename):
        try:
            # PDF boyutu ve yönlendirme seçimi
            orientation_win = tk.Toplevel(self.root)
            orientation_win.title("PDF Ayarları")
            orientation_win.geometry("300x250")
            
            # Sayfa boyutu
            tk.Label(orientation_win, text="Sayfa Boyutu:").pack(pady=5)
            page_size = tk.StringVar(value="A4")
            page_frame = tk.Frame(orientation_win)
            page_frame.pack()
            
            tk.Radiobutton(page_frame, text="A4", variable=page_size, value="A4").pack(side="left")
            tk.Radiobutton(page_frame, text="Letter", variable=page_size, value="Letter").pack(side="left")
            
            # Yönlendirme
            tk.Label(orientation_win, text="Yönlendirme:").pack(pady=5)
            orientation = tk.StringVar(value="landscape")
            orient_frame = tk.Frame(orientation_win)
            orient_frame.pack()
            
            tk.Radiobutton(orient_frame, text="Yatay (Landscape)", variable=orientation, value="landscape").pack()
            tk.Radiobutton(orient_frame, text="Dikey (Portrait)", variable=orientation, value="portrait").pack()
            
            # Katman seçimi
            tk.Label(orientation_win, text="Export Edilecek Katmanlar:").pack(pady=5)
            layer_vars = {}
            layer_frame = tk.Frame(orientation_win)
            layer_frame.pack()
            
            for layer_name in self.layers.keys():
                var = tk.BooleanVar(value=self.layers[layer_name]["visible"])
                layer_vars[layer_name] = var
                tk.Checkbutton(layer_frame, text=layer_name, variable=var).pack(anchor="w")
            
            # Ölçek
            tk.Label(orientation_win, text="Ölçek (0.1-2.0):").pack(pady=5)
            scale_var = tk.StringVar(value="1.0")
            scale_entry = tk.Entry(orientation_win, textvariable=scale_var, width=10)
            scale_entry.pack()
            
            result = [False]
            
            def create_pdf_with_settings():
                try:
                    scale = float(scale_var.get())
                    if not (0.1 <= scale <= 2.0):
                        messagebox.showerror("Hata", "Ölçek 0.1-2.0 arasında olmalı!")
                        return
                    
                    selected_layers = [name for name, var in layer_vars.items() if var.get()]
                    if not selected_layers:
                        messagebox.showerror("Hata", "En az bir katman seçmelisiniz!")
                        return
                    
                    self.generate_pdf(filename, page_size.get(), orientation.get(), selected_layers, scale)
                    result[0] = True
                    orientation_win.destroy()
                    
                except ValueError:
                    messagebox.showerror("Hata", "Geçerli bir ölçek değeri girin!")
            
            def cancel_export():
                orientation_win.destroy()
            
            btn_frame = tk.Frame(orientation_win)
            btn_frame.pack(pady=20)
            tk.Button(btn_frame, text="Export", command=create_pdf_with_settings).pack(side="left", padx=5)
            tk.Button(btn_frame, text="İptal", command=cancel_export).pack(side="left", padx=5)
            
            orientation_win.wait_window()
            
        except Exception as e:
            messagebox.showerror("PDF Export Hatası", str(e))

    def generate_pdf(self, filename, page_size, orientation, selected_layers, scale):
        # Canvas boyutlarını al
        canvas_items = self.canvas.find_all()
        if not canvas_items:
            messagebox.showwarning("Uyarı", "Export edilecek içerik yok!")
            return
        
        # Tüm objelerin sınırlarını hesapla
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for layer_name in selected_layers:
            if not self.layers[layer_name]["visible"]:
                continue
            
            # Requirements
            for num, info in self.requirements.items():
                if info.get("layer", "Requirements") == layer_name:
                    x, y = info["pos"]
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x + 160), max(max_y, y + 60)
            
            # Groups
            for group_id, info in self.groups.items():
                if info.get("layer", "Groups") == layer_name:
                    x, y = info["pos"]
                    w, h = info["size"]
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x + w), max(max_y, y + h)
            
            # Text boxes
            for text_id, info in self.text_boxes.items():
                if info.get("layer", "Notes") == layer_name:
                    x, y = info["pos"]
                    w, h = info["size"]
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x + w), max(max_y, y + h)
        
        if min_x == float('inf'):
            messagebox.showwarning("Uyarı", "Seçilen katmanlarda görünür içerik yok!")
            return
        
        # Sayfa boyutunu ayarla
        if page_size == "A4":
            page_width, page_height = A4
        else:
            page_width, page_height = letter
        
        if orientation == "landscape":
            page_width, page_height = page_height, page_width
        
        # PDF oluştur
        c = pdf_canvas.Canvas(filename, pagesize=(page_width, page_height))
        
        # Başlık ekle
        c.setFont("Helvetica-Bold", 16)
        title = "Gereksinim Diagramı"
        c.drawString(50, page_height - 50, title)
        
        # Katman bilgisi
        c.setFont("Helvetica", 10)
        layer_info = f"Katmanlar: {', '.join(selected_layers)}"
        c.drawString(50, page_height - 70, layer_info)
        
        # Tarih
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.drawString(50, page_height - 90, f"Oluşturulma: {date_str}")
        
        # Çizim alanını hesapla
        content_width = max_x - min_x
        content_height = max_y - min_y
        
        # Sayfa marjinleri
        margin = 50
        available_width = page_width - 2 * margin
        available_height = page_height - 150  # Başlık için alan bırak
        
        # Ölçeklemeyi hesapla
        scale_x = available_width / content_width
        scale_y = available_height / content_height
        final_scale = min(scale_x, scale_y, scale)  # Kullanıcı ölçeği de dikkate al
        
        # Çizim offset'ini hesapla
        scaled_width = content_width * final_scale
        scaled_height = content_height * final_scale
        offset_x = margin + (available_width - scaled_width) / 2
        offset_y = margin + (available_height - scaled_height) / 2
        
        # PDF koordinat sistemi (sol alt köşe origin)
        def transform_coords(x, y):
            pdf_x = offset_x + (x - min_x) * final_scale
            pdf_y = page_height - offset_y - (y - min_y) * final_scale
            return pdf_x, pdf_y
        
        # Grupları çiz (background)
        for group_id, info in self.groups.items():
            layer = info.get("layer", "Groups")
            if layer not in selected_layers:
                continue
            
            x, y = info["pos"]
            w, h = info["size"]
            
            pdf_x, pdf_y = transform_coords(x, y + h)  # Sol alt köşe
            pdf_w = w * final_scale
            pdf_h = h * final_scale
            
            # Grup kutusu
            c.setFillColorRGB(1, 1, 0.8)  # Açık sarı
            c.setStrokeColor(black)
            c.rect(pdf_x, pdf_y, pdf_w, pdf_h, fill=1, stroke=1)
            
            # Grup adı
            c.setFillColor(black)
            c.setFont("Helvetica-Bold", max(8, int(10 * final_scale)))
            c.drawString(pdf_x + 5, pdf_y + pdf_h - 15, info["name"])
        
        # Gereksinimleri çiz
        for num, info in self.requirements.items():
            layer = info.get("layer", "Requirements")
            if layer not in selected_layers:
                continue
            
            x, y = info["pos"]
            pdf_x, pdf_y = transform_coords(x, y + 60)  # Sol alt köşe
            
            # Gereksinim kutusu
            color = info.get("color", "lightblue")
            if color == "lightgreen":
                c.setFillColorRGB(0.8, 1, 0.8)
            elif color == "lightblue":
                c.setFillColorRGB(0.8, 0.8, 1)
            elif color == "lightcoral":
                c.setFillColorRGB(1, 0.8, 0.8)
            else:
                c.setFillColorRGB(0.9, 0.9, 0.9)
            
            c.setStrokeColor(black)
            box_width = 160 * final_scale
            box_height = 60 * final_scale
            c.rect(pdf_x, pdf_y, box_width, box_height, fill=1, stroke=1)
            
            # Yazılar
            c.setFillColor(black)
            font_size = max(6, int(10 * final_scale))
            c.setFont("Helvetica-Bold", font_size)
            
            # Başlık (üstte)
            text_x = pdf_x + box_width/2
            text_y = pdf_y + box_height - 15
            
            # Metni ortala
            text_width = c.stringWidth(info["text"], "Helvetica-Bold", font_size)
            c.drawString(pdf_x + (box_width - text_width)/2, text_y, info["text"])
            
            # ID (ortada)
            c.setFont("Helvetica", max(5, int(8 * final_scale)))
            id_text = f"ID: {info['id']}"
            id_width = c.stringWidth(id_text, "Helvetica", max(5, int(8 * final_scale)))
            c.drawString(pdf_x + (box_width - id_width)/2, text_y - 15, id_text)
            
            # Alt gereksinimler (altta)
            if info["children"]:
                children_text = f"Alt: {info['children']}"
                children_width = c.stringWidth(children_text, "Helvetica", max(5, int(8 * final_scale)))
                c.drawString(pdf_x + (box_width - children_width)/2, text_y - 30, children_text)
        
        # Text box'ları çiz
        for text_id, info in self.text_boxes.items():
            layer = info.get("layer", "Notes")
            if layer not in selected_layers:
                continue
            
            x, y = info["pos"]
            w, h = info["size"]
            pdf_x, pdf_y = transform_coords(x, y + h)  # Sol alt köşe
            
            # Text box
            c.setFillColorRGB(1, 1, 1)  # Beyaz
            c.setStrokeColor(black)
            box_width = w * final_scale
            box_height = h * final_scale
            c.rect(pdf_x, pdf_y, box_width, box_height, fill=1, stroke=1)
            
            # İçerik
            c.setFillColor(black)
            font_size = max(6, int(info["font_size"] * final_scale))
            c.setFont("Helvetica", font_size)
            
            # Metin satırları halinde böl (uzun metinler için)
            content = info["content"]
            max_width = box_width - 10  # Padding
            
            # Basit metin sarma
            if c.stringWidth(content, "Helvetica", font_size) <= max_width:
                c.drawString(pdf_x + 5, pdf_y + box_height/2, content)
            else:
                # Metni kelimelere böl ve satırlara sığdır
                words = content.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if c.stringWidth(test_line, "Helvetica", font_size) <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                
                if current_line:
                    lines.append(current_line)
                
                # Satırları çiz
                line_height = font_size + 2
                start_y = pdf_y + box_height/2 + (len(lines) * line_height) / 2
                
                for i, line in enumerate(lines[:3]):  # Maksimum 3 satır
                    c.drawString(pdf_x + 5, start_y - i * line_height, line)
                
                if len(lines) > 3:
                    c.drawString(pdf_x + 5, start_y - 3 * line_height, "...")
        
        # Bağlantıları çiz
        c.setStrokeColor(red)
        c.setLineWidth(2)
        
        for parent, children in self.links.items():
            if parent not in self.requirements:
                continue
            
            parent_layer = self.requirements[parent].get("layer", "Requirements")
            if parent_layer not in selected_layers:
                continue
            
            parent_x, parent_y = self.requirements[parent]["pos"]
            px, py = parent_x + 80, parent_y + 60  # Alt orta
            pdf_px, pdf_py = transform_coords(px, py)
            
            for child in children:
                if child not in self.requirements:
                    continue
                
                child_layer = self.requirements[child].get("layer", "Requirements")
                if child_layer not in selected_layers:
                    continue
                
                child_x, child_y = self.requirements[child]["pos"]
                cx, cy = child_x + 80, child_y  # Üst orta
                pdf_cx, pdf_cy = transform_coords(cx, cy)
                
                # Ok çiz
                c.line(pdf_px, pdf_py, pdf_cx, pdf_cy)
                
                # Ok ucu
                arrow_size = 5 * final_scale
                c.line(pdf_cx, pdf_cy, pdf_cx - arrow_size, pdf_cy + arrow_size)
                c.line(pdf_cx, pdf_cy, pdf_cx + arrow_size, pdf_cy + arrow_size)
        
        # Ölçek bilgisi
        c.setFont("Helvetica", 8)
        c.drawString(margin, 30, f"Ölçek: {final_scale:.2f}")
        
        # PDF'i kaydet
        c.save()
        messagebox.showinfo("Başarılı", f"PDF başarıyla kaydedildi:\n{filename}")

    def export_to_png(self):
        # Dosya kaydetme penceresi
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="PNG olarak kaydet"
        )
        
        if not filename:
            return
        
        self.create_png(filename)

    def create_png(self, filename):
        try:
            # PNG export ayarları penceresi
            png_win = tk.Toplevel(self.root)
            png_win.title("PNG Export Ayarları")
            png_win.geometry("300x250")
            
            # Başlık
            tk.Label(png_win, text="PNG Screenshot Export", 
                    font=("Arial", 12, "bold")).pack(pady=10)
            
            # Katman seçimi
            tk.Label(png_win, text="Export Edilecek Katmanlar:").pack(pady=(10,5))
            layer_vars = {}
            layer_frame = tk.Frame(png_win)
            layer_frame.pack()
            
            for layer_name in self.layers.keys():
                var = tk.BooleanVar(value=self.layers[layer_name]["visible"])
                layer_vars[layer_name] = var
                tk.Checkbutton(layer_frame, text=layer_name, variable=var).pack(anchor="w")
            
            # Kalite ayarları
            tk.Label(png_win, text="Export Ayarları:").pack(pady=(10,5))
            
            # Margin ayarı
            margin_frame = tk.Frame(png_win)
            margin_frame.pack()
            tk.Label(margin_frame, text="Margin (px):").pack(side="left")
            margin_var = tk.StringVar(value="20")
            tk.Entry(margin_frame, textvariable=margin_var, width=8).pack(side="left", padx=5)
            
            # Bilgi metni
            info_text = "Screenshot yöntemi diagramın görünen halini\nolduğu gibi PNG formatında kaydeder."
            tk.Label(png_win, text=info_text, font=("Arial", 9), 
                    fg="gray", justify="center").pack(pady=10)
            
            result = [False]
            
            def create_png_screenshot():
                try:
                    selected_layers = [name for name, var in layer_vars.items() if var.get()]
                    if not selected_layers:
                        messagebox.showerror("Hata", "En az bir katman seçmelisiniz!")
                        return
                    
                    try:
                        margin = int(margin_var.get())
                        if margin < 0 or margin > 100:
                            raise ValueError()
                    except ValueError:
                        messagebox.showerror("Hata", "Margin 0-100 arasında bir sayı olmalı!")
                        return
                    
                    self.export_png_screenshot(filename, selected_layers, margin)
                    result[0] = True
                    png_win.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Export Hatası", str(e))
            
            def cancel_export():
                png_win.destroy()
            
            btn_frame = tk.Frame(png_win)
            btn_frame.pack(pady=15)
            tk.Button(btn_frame, text="Export", command=create_png_screenshot, 
                     bg="lightgreen", width=10).pack(side="left", padx=5)
            tk.Button(btn_frame, text="İptal", command=cancel_export, 
                     width=10).pack(side="left", padx=5)
            
            png_win.wait_window()
            
        except Exception as e:
            messagebox.showerror("PNG Export Hatası", str(e))

    def export_png_screenshot(self, filename, selected_layers, margin):
        """Screenshot yöntemi ile PNG export"""
        try:
            # Katman görünürlüğünü geçici olarak ayarla
            original_visibility = {}
            for layer_name in self.layers:
                original_visibility[layer_name] = self.layers[layer_name]["visible"]
                self.layers[layer_name]["visible"] = layer_name in selected_layers
            
            self.update_canvas_visibility()
            self.root.update()  # Canvas'ı güncelle
            
            # Canvas koordinatlarını al
            bbox = self.canvas.bbox("all")
            if not bbox:
                messagebox.showwarning("Uyarı", "Export edilecek içerik yok!")
                return
            
            x1, y1, x2, y2 = bbox
            x1 -= margin
            y1 -= margin
            x2 += margin
            y2 += margin
            
            # Canvas'ın ekrandaki pozisyonunu al
            canvas_x = self.canvas.winfo_rootx()
            canvas_y = self.canvas.winfo_rooty()
            
            # Scroll pozisyonunu dikkate al
            scroll_x = self.canvas.canvasx(0)
            scroll_y = self.canvas.canvasy(0)
            
            # Ekran koordinatlarını hesapla
            screen_x1 = int(canvas_x + x1 - scroll_x)
            screen_y1 = int(canvas_y + y1 - scroll_y)
            screen_x2 = int(canvas_x + x2 - scroll_x)
            screen_y2 = int(canvas_y + y2 - scroll_y)
            
            # Koordinat kontrolü
            if screen_x2 <= screen_x1 or screen_y2 <= screen_y1:
                messagebox.showerror("Hata", "Geçersiz screenshot koordinatları!")
                return
            
            try:
                # PIL ile screenshot
                from PIL import ImageGrab
                
                # Screenshot al
                screenshot = ImageGrab.grab(bbox=(screen_x1, screen_y1, screen_x2, screen_y2))
                
                # Dosyayı kaydet
                screenshot.save(filename, 'PNG', optimize=True, quality=95)
                
                # Başarı mesajı
                size_info = f"Boyut: {screen_x2-screen_x1}x{screen_y2-screen_y1} px"
                layer_info = f"Katmanlar: {', '.join(selected_layers)}"
                messagebox.showinfo("PNG Export Başarılı", 
                                   f"PNG başarıyla kaydedildi:\n{filename}\n\n{size_info}\n{layer_info}")
                
            except ImportError:
                messagebox.showerror("Kütüphane Eksik", 
                    "PNG export için PIL/Pillow kütüphanesi gerekli!\n\n" +
                    "Kurulum:\n" +
                    "pip install pillow")
            except Exception as screenshot_error:
                messagebox.showerror("Screenshot Hatası", 
                    f"Screenshot alınırken hata oluştu:\n{str(screenshot_error)}\n\n" +
                    "Çözüm önerileri:\n" +
                    "• Diagramın tamamen görünür olduğundan emin olun\n" +
                    "• Canvas'ın diğer pencerelerle örtüşmediğini kontrol edin\n" +
                    "• Zoom seviyesini ayarlayın")
            
        except Exception as e:
            messagebox.showerror("Export Hatası", str(e))
        
        finally:
            # Orijinal görünürlük ayarlarını geri yükle
            try:
                for layer_name, visible in original_visibility.items():
                    self.layers[layer_name]["visible"] = visible
                self.update_canvas_visibility()
            except Exception:
                # Hata olsa bile devam et
                pass

if __name__=="__main__":
    root=tk.Tk()
    app=RequirementApp(root)
    root.mainloop()