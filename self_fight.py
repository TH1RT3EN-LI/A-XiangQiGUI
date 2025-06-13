import subprocess
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import time
import os

MAX_MOVES = 300
LOG_FILE = "game_log.txt"

class XiangqiGUI:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1000x900")
        self.root.configure(bg='#f0f0f0')
        
        self.board = [['..' for _ in range(9)] for _ in range(10)]
        self.piece_positions = {}
        
        self.gameRunning = False
        self.is_paused = False
        self.manual_mode = tk.BooleanVar()
        self.humanVsEngine = tk.BooleanVar()  
        self.human_red = tk.BooleanVar(value=True) 
        self.show_chinese = tk.BooleanVar(value=True)
        self.wait_manual = False
        self.waitingHumanMove = False 
        self.currentMoveData = None
        
        self.isDragging = False
        self.draggedPiece = None
        self.dragFrom = None
        self.dragStartPos = None
        self.ghostPiece = None
        
        self.lastMoveMarker = None  
        
        self.engine1_path = tk.StringVar(value="请选择引擎1")
        self.engine2_path = tk.StringVar(value="请选择引擎2")
        
        self.create_widgets()
        self.init_board()
        self.update_display()
        self.setup_drag_events()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        engine_frame = ttk.LabelFrame(main_frame, text="引擎设置(需要导入输入输出与课设一样规范的.exe文件)", padding="10")
        engine_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        mode_frame = ttk.Frame(engine_frame)
        mode_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="Engine vs Engine", variable=self.humanVsEngine, 
                       value=False, command=self.on_mode_change).grid(row=0, column=0, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="人机对弈", variable=self.humanVsEngine, 
                       value=True, command=self.on_mode_change).grid(row=0, column=1, padx=(0, 20))
        
        self.roleFrame = ttk.Frame(engine_frame)
        self.roleFrame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.roleFrame, text="玩家执:").grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(self.roleFrame, text="红方(先手)", variable=self.human_red, 
                       value=True).grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(self.roleFrame, text="黑方(后手)", variable=self.human_red, 
                       value=False).grid(row=0, column=2)
        
        self.e1_frame = ttk.Frame(engine_frame)
        self.e1_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Label(self.e1_frame, text="红方引擎:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.engine1_label = ttk.Label(self.e1_frame, textvariable=self.engine1_path, 
                                      relief="sunken", width=40, foreground="gray")
        self.engine1_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.engine1_btn = ttk.Button(self.e1_frame, text="浏览", command=self.select_engine1)
        self.engine1_btn.grid(row=0, column=2)
        
        self.e2_frame = ttk.Frame(engine_frame)
        self.e2_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Label(self.e2_frame, text="黑方引擎:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.engine2_label = ttk.Label(self.e2_frame, textvariable=self.engine2_path, 
                                      relief="sunken", width=40, foreground="gray")
        self.engine2_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.engine2_btn = ttk.Button(self.e2_frame, text="浏览", command=self.select_engine2)
        self.engine2_btn.grid(row=0, column=2)
        
        engine_frame.columnconfigure(1, weight=1)
        
        board_frame = ttk.LabelFrame(main_frame, text="棋盘", padding="15")
        board_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 15))
        
        display_frame = ttk.Frame(board_frame)
        display_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(display_frame, text="棋子显示:").grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(display_frame, text="汉字", variable=self.show_chinese, 
                       value=True, command=self.on_display_change).grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(display_frame, text="标签", variable=self.show_chinese, 
                       value=False, command=self.on_display_change).grid(row=0, column=2)
        
        self.canvas = tk.Canvas(board_frame, width=450, height=500, bg='#B28C70', relief="solid", borderwidth=2)
        self.canvas.grid(row=1, column=0, padx=10, pady=10)
        
        self.draw_board_lines()
        
        self.boardLabels = []
        for y in range(10):
            row_labels = []
            for x in range(9):
                canvas_x = 50 + x * 45
                canvas_y = 50 + (9-y) * 45
                
                circle = self.canvas.create_oval(canvas_x-18, canvas_y-18, canvas_x+18, canvas_y+18, 
                                               fill="", outline="", width=0)
                
                text = self.canvas.create_text(canvas_x, canvas_y, text="..", 
                                             font=("Microsoft YaHei", 12, "bold"), fill='black')
                
                row_labels.append((circle, text))
            self.boardLabels.append(row_labels)
        
        info_frame = ttk.LabelFrame(main_frame, text="对局信息", padding="15")
        info_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        status_frame = ttk.Frame(info_frame)
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.moveLabel = ttk.Label(status_frame, text="当前步数: 0", font=("Microsoft YaHei", 12, "bold"))
        self.moveLabel.grid(row=0, column=0, sticky=tk.W, pady=3)
        
        self.playerLabel = ttk.Label(status_frame, text="当前玩家: 红方", font=("Microsoft YaHei", 12, "bold"))
        self.playerLabel.grid(row=1, column=0, sticky=tk.W, pady=3)
        
        self.lastMoveLabel = ttk.Label(status_frame, text="最后一步: -", font=("Microsoft YaHei", 11))
        self.lastMoveLabel.grid(row=2, column=0, sticky=tk.W, pady=3)
        
        manual_frame = ttk.LabelFrame(info_frame, text="控制模式", padding="10")
        manual_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        manual_check = ttk.Checkbutton(manual_frame, text="手动下一步", variable=self.manual_mode,
                         command=self.on_manual_mode_change)
        manual_check.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.nextStepBtn = ttk.Button(manual_frame, text="下一步", command=self.manual_next_step,
                                         state="disabled")
        self.nextStepBtn.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        log_frame = ttk.LabelFrame(info_frame, text="对局日志", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.logText = tk.Text(log_frame, width=45, height=15, font=("Microsoft YaHei", 9),
                               wrap=tk.WORD, bg='#f8f8f8', relief="solid", borderwidth=1)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.logText.yview)
        self.logText.configure(yscrollcommand=scrollbar.set)
        self.logText.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.startBtn = ttk.Button(button_frame, text="开始对局", command=self.start_game,
                                     style="Accent.TButton")
        self.startBtn.grid(row=0, column=0, padx=8)
        
        self.pauseBtn = ttk.Button(button_frame, text="暂停", command=self.toggle_pause, 
                                     state="disabled")
        self.pauseBtn.grid(row=0, column=1, padx=8)
        
        self.resetBtn = ttk.Button(button_frame, text="重置", command=self.reset_game)
        self.resetBtn.grid(row=0, column=2, padx=8)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        info_frame.rowconfigure(2, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.on_mode_change()
    
    def on_mode_change(self):
        if self.humanVsEngine.get():
            self.roleFrame.grid()
            self.e2_frame.grid_remove()
            ttk.Label(self.e1_frame, text="对手引擎:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            self.log_message("切换到人机对弈模式")
        else:
            self.roleFrame.grid_remove()
            self.e2_frame.grid()
            ttk.Label(self.e1_frame, text="红方引擎:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            self.log_message("切换到自博模式")
    
    def on_display_change(self):
        display_mode = "汉字" if self.show_chinese.get() else "标签"
        self.log_message(f"切换到{display_mode}显示模式")
        self.update_display()
    
    def setup_drag_events(self):
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
    
    def on_drag_start(self, event):
        if not self.humanVsEngine.get() or not self.waitingHumanMove:
            return
        
        x, y = self.canvas_to_board(event.x, event.y)
        if x is None or y is None:
            return
        
        piece = self.board[y][x]
        if piece == '..':
            return
        
        current_is_red = (self.currentSide == 0)
        piece_is_red = piece.islower()
        
        if self.human_red.get():
            if not (current_is_red and piece_is_red):
                return
        else:
            if not (not current_is_red and not piece_is_red):
                return
        
        self.isDragging = True
        self.draggedPiece = piece
        self.dragFrom = (x, y)
        self.dragStartPos = (event.x, event.y)
        
        circle, text = self.boardLabels[y][x]
        self.canvas.itemconfig(circle, outline='red', width=3)
        
        self.create_ghost_piece(event.x, event.y, piece)
        
        self.canvas.itemconfig(text, fill='', state='disabled')
        self.canvas.itemconfig(circle, fill='', outline='red', width=3)
    
    def create_ghost_piece(self, x, y, piece):
        chinese_names = {
            'k': '帅', 'K': '将',
            'a1': '仕', 'a2': '仕', 'A1': '士', 'A2': '士',
            'b1': '相', 'b2': '相', 'B1': '象', 'B2': '象',
            'n1': '马', 'n2': '马', 'N1': '马', 'N2': '马',
            'r1': '车', 'r2': '车', 'R1': '车', 'R2': '车',
            'c1': '炮', 'c2': '炮', 'C1': '炮', 'C2': '炮',
            'p1': '兵', 'p2': '兵', 'p3': '兵', 'p4': '兵', 'p5': '兵',
            'P1': '卒', 'P2': '卒', 'P3': '卒', 'P4': '卒', 'P5': '卒',
        }
        
        if piece.islower():  
            ghost_circle = self.canvas.create_oval(x-18, y-18, x+18, y+18, 
                                                 fill='#F5DEB3', outline='#8B4513', 
                                                 width=2, stipple='gray50')
            if self.show_chinese.get():
                display_text = chinese_names.get(piece, piece)
                font_style = ("KaiTi", 13, "bold")
            else:
                display_text = piece
                font_style = ("Consolas", 10, "bold")
            
            ghost_text = self.canvas.create_text(x, y, text='',
                                               fill='#A52A2A', font=font_style,
                                               stipple='gray50')
        else:  
            ghost_circle = self.canvas.create_oval(x-18, y-18, x+18, y+18, 
                                                 fill='#DEB887', outline='#5C4033', 
                                                 width=2, stipple='gray50')
            if self.show_chinese.get():
                display_text = chinese_names.get(piece, piece)
                font_style = ("KaiTi", 13, "bold")
            else:
                display_text = piece
                font_style = ("Consolas", 10, "bold")
            
            ghost_text = self.canvas.create_text(x, y, text='',
                                               fill='#000000', font=font_style,
                                               stipple='gray50')
        
        self.ghostPiece = (ghost_circle, ghost_text)
    
    def on_drag_motion(self, event):
        if not self.isDragging or not self.ghostPiece:
            return
        
        ghost_circle, ghost_text = self.ghostPiece
        
        dx = event.x - self.dragStartPos[0]
        dy = event.y - self.dragStartPos[1]
        
        self.canvas.coords(ghost_circle, event.x-18, event.y-18, event.x+18, event.y+18)
        self.canvas.coords(ghost_text, event.x, event.y)
        
        self.dragStartPos = (event.x, event.y)
    
    def on_drag_end(self, event):
        if not self.isDragging:
            return
        
        if self.ghostPiece:
            ghost_circle, ghost_text = self.ghostPiece
            self.canvas.delete(ghost_circle)
            self.canvas.delete(ghost_text)
            self.ghostPiece = None
        
        if self.dragFrom:
            y = self.dragFrom[1]
            x = self.dragFrom[0]
            circle, text = self.boardLabels[y][x]
            self.canvas.itemconfig(circle, outline='', width=0)
            self.canvas.itemconfig(text, state='normal')
            self.update_single_position(x, y)
        
        to_x, to_y = self.canvas_to_board(event.x, event.y)
        
        if to_x is not None and to_y is not None and self.dragFrom:
            from_x, from_y = self.dragFrom
            
            if (from_x, from_y) != (to_x, to_y):
                move_cmd = f"{self.draggedPiece} {to_x} {to_y}"
                self.humanMove = move_cmd
                self.waitingHumanMove = False
                self.log_message(f"人类走棋: {move_cmd}")
        
        self.isDragging = False
        self.draggedPiece = None
        self.dragFrom = None
        self.dragStartPos = None
    
    def update_single_position(self, x, y):
        chinese_names = {
            'k': '帅', 'K': '将',
            'a1': '仕', 'a2': '仕', 'A1': '士', 'A2': '士',
            'b1': '相', 'b2': '相', 'B1': '象', 'B2': '象',
            'n1': '马', 'n2': '马', 'N1': '马', 'N2': '马',
            'r1': '车', 'r2': '车', 'R1': '车', 'R2': '车',
            'c1': '炮', 'c2': '炮', 'C1': '炮', 'C2': '炮',
            'p1': '兵', 'p2': '兵', 'p3': '兵', 'p4': '兵', 'p5': '兵',
            'P1': '卒', 'P2': '卒', 'P3': '卒', 'P4': '卒', 'P5': '卒',
        }
        
        piece = self.board[y][x]
        circle, text = self.boardLabels[y][x]
        
        if piece == '..':
            self.canvas.itemconfig(text, text='', fill='black')
            self.canvas.itemconfig(circle, fill='', outline='', width=0)
        elif piece.islower():  
            self.canvas.itemconfig(circle,
                                fill='#F5DEB3',         
                                outline='#8B4513')      
            
            if self.show_chinese.get():
                display_text = chinese_names.get(piece, piece)
                font_style = ("KaiTi", 13, "bold")
            else:
                display_text = piece
                font_style = ("Consolas", 10, "bold")
            
            self.canvas.itemconfig(text,
                                text=display_text,
                                fill='#A52A2A',          
                                font=font_style)
        else:  
            self.canvas.itemconfig(circle,
                                fill='#DEB887',         
                                outline='#5C4033')      
            
            if self.show_chinese.get():
                display_text = chinese_names.get(piece, piece)
                font_style = ("KaiTi", 13, "bold")
            else:
                display_text = piece
                font_style = ("Consolas", 10, "bold")
            
            self.canvas.itemconfig(text,
                                text=display_text,
                                fill='#000000',          
                                font=font_style)
    
    def add_move_marker(self, from_x, from_y):
        if self.lastMoveMarker:
            self.canvas.delete(self.lastMoveMarker)
        
        canvas_x = 50 + from_x * 45
        canvas_y = 50 + (9-from_y) * 45
        
        self.lastMoveMarker = self.canvas.create_oval(canvas_x-5, canvas_y-5, canvas_x+5, canvas_y+5,
                                                       fill='#FF6B6B', outline='#D63031', width=2)
    
    def canvas_to_board(self, canvas_x, canvas_y):
        if canvas_x < 32 or canvas_x > 428 or canvas_y < 32 or canvas_y > 468:
            return None, None
        
        x = round((canvas_x - 50) / 45)
        y = round((canvas_y - 50) / 45)
        
        if x < 0 or x > 8 or y < 0 or y > 9:
            return None, None
        
        board_y = 9 - y
        
        return x, board_y
    
    def select_engine1(self):
        filename = filedialog.askopenfilename(
            title="选择红方引擎" if not self.humanVsEngine.get() else "选择对手引擎",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.engine1_path.set(filename)
            self.engine1_label.config(foreground="black")
            self.log_message(f"引擎已设置: {os.path.basename(filename)}")
    
    def select_engine2(self):
        filename = filedialog.askopenfilename(
            title="选择黑方引擎",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.engine2_path.set(filename)
            self.engine2_label.config(foreground="black")
            self.log_message(f"黑方引擎已设置: {os.path.basename(filename)}")
    
    def use_same_engine(self):
        filename = filedialog.askopenfilename(
            title="选择象棋引擎",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.engine1_path.set(filename)
            self.engine2_path.set(filename)
            self.engine1_label.config(foreground="black")
            self.engine2_label.config(foreground="black")
            self.log_message(f"双方引擎已设置为: {os.path.basename(filename)}")
    
    def validate_engines(self):
        engine1 = self.engine1_path.get()
        
        if engine1 == "请选择引擎1" or not os.path.exists(engine1):
            if self.humanVsEngine.get():
                tk.messagebox.showerror("错误", "请选择有效的对手引擎文件")
            else:
                tk.messagebox.showerror("错误", "请选择有效的红方引擎文件")
            return False
        
        if not self.humanVsEngine.get():
            engine2 = self.engine2_path.get()
            if engine2 == "请选择引擎2" or not os.path.exists(engine2):
                tk.messagebox.showerror("错误", "请选择有效的黑方引擎文件")
                return False
        
        return True
    
    def draw_board_lines(self):
        for x in range(9):
            x_pos = 50 + x * 45
            self.canvas.create_line(x_pos, 50, x_pos, 455, fill='black', width=2)
        
        for y in range(10):
            y_pos = 50 + y * 45
            if y == 4:  
                self.canvas.create_line(50, y_pos, 410, y_pos, fill='black', width=2)
            elif y == 5:  
                self.canvas.create_line(50, y_pos, 410, y_pos, fill='black', width=2)
            else:
                self.canvas.create_line(50, y_pos, 410, y_pos, fill='black', width=2)
        
        self.canvas.create_line(185, 50, 275, 140, fill='black', width=2)
        self.canvas.create_line(275, 50, 185, 140, fill='black', width=2)
        
        self.canvas.create_line(185, 365, 275, 455, fill='black', width=2)
        self.canvas.create_line(275, 365, 185, 455, fill='black', width=2)
        
        self.canvas.create_text(250, 250, text="楚河                汉界", 
                            font=("Microsoft YaHei", 14, "bold"), fill="#000000")
    
    def update_display(self):
        chinese_names = {
            'k': '帅', 'K': '将',
            'a1': '仕', 'a2': '仕', 'A1': '士', 'A2': '士',
            'b1': '相', 'b2': '相', 'B1': '象', 'B2': '象',
            'n1': '马', 'n2': '马', 'N1': '马', 'N2': '马',
            'r1': '车', 'r2': '车', 'R1': '车', 'R2': '车',
            'c1': '炮', 'c2': '炮', 'C1': '炮', 'C2': '炮',
            'p1': '兵', 'p2': '兵', 'p3': '兵', 'p4': '兵', 'p5': '兵',
            'P1': '卒', 'P2': '卒', 'P3': '卒', 'P4': '卒', 'P5': '卒',
        }
        
        for y in range(10):
            for x in range(9):
                piece = self.board[y][x]
                circle, text = self.boardLabels[y][x]
                
                if piece == '..':
                    self.canvas.itemconfig(text, text='', fill='black')
                    self.canvas.itemconfig(circle, fill='', outline='', width=0)
                elif piece.islower():  
                    self.canvas.itemconfig(circle,
                                        fill='#F5DEB3',         
                                        outline='#8B4513')      
                    
                    if self.show_chinese.get():
                        display_text = chinese_names.get(piece, piece)
                        font_style = ("KaiTi", 13, "bold")
                    else:
                        display_text = piece
                        font_style = ("Consolas", 10, "bold")
                    
                    self.canvas.itemconfig(text,
                                        text=display_text,
                                        fill='#A52A2A',          
                                        font=font_style)
                else:  
                    self.canvas.itemconfig(circle,
                                        fill='#DEB887',         
                                        outline='#5C4033')      
                    
                    if self.show_chinese.get():
                        display_text = chinese_names.get(piece, piece)
                        font_style = ("KaiTi", 13, "bold")
                    else:
                        display_text = piece
                        font_style = ("Consolas", 10, "bold")
                    
                    self.canvas.itemconfig(text,
                                        text=display_text,
                                        fill='#000000',          
                                        font=font_style)
        
    def init_board(self):
        red_setup = [
            ('r1', 0, 0), ('b1', 2, 0), ('a1', 3, 0), ('k', 4, 0), 
            ('a2', 5, 0), ('b2', 6, 0), ('n2', 7, 0), ('r2', 8, 0),
            ('c1', 1, 2), ('c2', 7, 2),
            ('p1', 0, 3), ('p2', 2, 3), ('p3', 4, 3), ('p4', 6, 3), ('p5', 8, 3),
        ]
        black_setup = [
            ('R2', 0, 9), ('N2', 1, 9), ('B2', 2, 9), ('A2', 3, 9), ('K', 4, 9), 
            ('A1', 5, 9), ('B1', 6, 9),  ('R1', 8, 9),
            ('C2', 1, 7), ('C1', 7, 7),
            ('P5', 0, 6), ('P4', 2, 6), ('P3', 4, 6), ('P2', 6, 6), ('P1', 8, 6),
        ]
        
        for pid, x, y in red_setup + black_setup:
            self.board[y][x] = pid
            self.piece_positions[pid] = (x, y)
    
    def on_manual_mode_change(self):
        if self.manual_mode.get():
            self.nextStepBtn.config(state="normal" if self.wait_manual else "disabled")
            self.log_message("已启用手动下一步")
        else:
            self.nextStepBtn.config(state="disabled")
            self.log_message("已禁用手动下一步")
    
    def manual_next_step(self):
        if self.wait_manual and self.currentMoveData:
            self.wait_manual = False
            self.nextStepBtn.config(state="disabled")
            self.execute_move_step()
    
    def log_message(self, message):
        self.logText.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.logText.see(tk.END)
        self.root.update()
    
    def mirror_move(self, mv):
        pid, xs, ys = mv.split()
        x, y = int(xs), int(ys)
        mx, my = 8 - x, 9 - y
        return f"{pid.upper()} {mx} {my}"
    
    def reverse_mirror_move(self, mv):
        pid, xs, ys = mv.split()
        x, y = int(xs), int(ys)
        mx, my = 8 - x, 9 - y
        return f"{pid} {mx} {my}"
    
    def read_move(self, proc):
        while True:
            line = proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if line:
                return line
    
    def get_human_move(self):
        self.waitingHumanMove = True
        self.humanMove = None
        self.log_message("等待 你 走棋（拖动棋子到目标位置）...")
        
        while self.waitingHumanMove and self.gameRunning:
            time.sleep(0.1)
        
        return self.humanMove if self.gameRunning else None
    
    def start_game(self):
        if self.gameRunning:
            return
        
        if not self.validate_engines():
            return
            
        self.startBtn.config(state="disabled")
        self.pauseBtn.config(state="normal")
        self.gameRunning = True
        
        self.board = [['..' for _ in range(9)] for _ in range(10)]
        self.piece_positions = {}
        self.init_board()
        self.update_display()
        
        if self.lastMoveMarker:
            self.canvas.delete(self.lastMoveMarker)
            self.lastMoveMarker = None
        
        if self.humanVsEngine.get():
            self.log_message("=== 开始人机对弈 ===")
            self.log_message(f"你 执: {'红方(先手)' if self.human_red.get() else '黑方(后手)'}")
        else:
            self.log_message("=== 开始引擎自博 ===")
        
        if self.humanVsEngine.get():
            game_thread = threading.Thread(target=self.play_human_vs_engine)
        else:
            game_thread = threading.Thread(target=self.play_engine_vs_engine)
        game_thread.daemon = True
        game_thread.start()
    
    def play_human_vs_engine(self):
        engine_path = self.engine1_path.get()
        
        try:
            engine = subprocess.Popen(
                [engine_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1
            )
            
            self.log_message("引擎启动成功")
            self.log_message(f"对手引擎: {os.path.basename(engine_path)}")
            
            if not self.human_red.get():
                engine.stdin.write("START\n")
                engine.stdin.flush()
            
            self.currentSide = 0  
            
            for move_no in range(1, MAX_MOVES + 1):
                if not self.gameRunning:
                    break
                    
                while self.is_paused and self.gameRunning:
                    time.sleep(0.1)
                
                if not self.gameRunning:
                    break
                
                current_is_red = (self.currentSide == 0)
                player_name = "红方" if current_is_red else "黑方"
                
                self.root.after(0, lambda: self.moveLabel.config(text=f"当前步数: {move_no}"))
                self.root.after(0, lambda: self.playerLabel.config(text=f"当前玩家: {player_name}"))
                
                human_turn = (current_is_red and self.human_red.get()) or (not current_is_red and not self.human_red.get())
                
                if human_turn:
                    self.log_message(f"第 {move_no} 步，轮到 你 走棋...")
                    mv = self.get_human_move()
                    if mv is None:
                        break
                    
                    if self.human_red.get():
                        engine_move = self.reverse_mirror_move(mv)
                    else:
                        engine_move = mv
                    
                    engine.stdin.write(engine_move + "\n")
                    engine.stdin.flush()
                    
                else:
                    self.log_message(f"第 {move_no} 步，等待引擎走棋...")
                    mv = self.read_move(engine)
                    if mv is None:
                        self.log_message("引擎意外终止")
                        break
                    
                    if self.human_red.get():
                        mv = self.mirror_move(mv)
                
                self.execute_move_display(mv, player_name, move_no)
                
                self.currentSide ^= 1
                time.sleep(0.5)  
            
            self.log_message(f"对局结束，共走 {move_no} 步")
            engine.terminate()
            
        except Exception as e:
            self.log_message(f"错误: {e}")
        finally:
            self.gameRunning = False
            self.waitingHumanMove = False
            self.root.after(0, lambda: self.startBtn.config(state="normal"))
            self.root.after(0, lambda: self.pauseBtn.config(state="disabled"))
    
    def play_engine_vs_engine(self):
        engine1_path = self.engine1_path.get()
        engine2_path = self.engine2_path.get()
        
        try:
            e1 = subprocess.Popen(
                [engine1_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1
            )
            e2 = subprocess.Popen(
                [engine2_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1
            )
            
            self.log_message("引擎启动成功")
            self.log_message(f"红方(先手): {os.path.basename(engine1_path)}")
            self.log_message(f"黑方(后手): {os.path.basename(engine2_path)}")
            
            e1.stdin.write("START\n")
            e1.stdin.flush()
            
            players = [(e1, e2, "红方"), (e2, e1, "黑方")]
            side = 0
            
            for move_no in range(1, MAX_MOVES + 1):
                if not self.gameRunning:
                    break
                    
                while self.is_paused and self.gameRunning:
                    time.sleep(0.1)
                
                if not self.gameRunning:
                    break
                
                engine, opponent, player_name = players[side]
                
                self.root.after(0, lambda: self.moveLabel.config(text=f"当前步数: {move_no}"))
                self.root.after(0, lambda: self.playerLabel.config(text=f"当前玩家: {player_name}"))
                
                self.log_message(f"第 {move_no} 步，等待 {player_name} 出招...")
                
                mv = self.read_move(engine)
                if mv is None:
                    self.log_message("引擎意外终止")
                    break
                
                if self.manual_mode.get():
                    self.currentMoveData = (mv, side, move_no, players)
                    self.wait_manual = True
                    self.root.after(0, lambda: self.nextStepBtn.config(state="normal"))
                    self.log_message(f"等待手动确认执行: {player_name} {mv}")
                    
                    while self.wait_manual and self.gameRunning:
                        time.sleep(0.1)
                    
                    if not self.gameRunning:
                        break
                else:
                    self.currentMoveData = (mv, side, move_no, players)
                    self.execute_move_step()
                    time.sleep(1)  
                
                side ^= 1
            
            self.log_message(f"对局结束，共走 {move_no} 步")
            e1.terminate()
            e2.terminate()
            
        except Exception as e:
            self.log_message(f"错误: {e}")
        finally:
            self.gameRunning = False
            self.wait_manual = False
            self.root.after(0, lambda: self.startBtn.config(state="normal"))
            self.root.after(0, lambda: self.pauseBtn.config(state="disabled"))
            self.root.after(0, lambda: self.nextStepBtn.config(state="disabled"))
    
    def execute_move_display(self, mv, player_name, move_no):
        self.log_message(f"{player_name}: {mv}")
        self.root.after(0, lambda m=mv: self.lastMoveLabel.config(text=f"最后一步: {m}"))
        
        pid, xs, ys = mv.split()
        x, y = int(xs), int(ys)
        
        from_x, from_y = None, None
        if pid in self.piece_positions:
            from_x, from_y = self.piece_positions[pid]
        
        if pid in self.piece_positions:
            ox, oy = self.piece_positions[pid]
            self.board[oy][ox] = '..'
        self.piece_positions[pid] = (x, y)
        self.board[y][x] = pid
        
        self.root.after(0, self.update_display)
        
        if from_x is not None and from_y is not None:
            self.root.after(0, lambda: self.add_move_marker(from_x, from_y))
    
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pauseBtn.config(text="继续" if self.is_paused else "暂停")
        self.log_message("游戏已暂停" if self.is_paused else "游戏已继续")
    
    def reset_game(self):
        self.gameRunning = False
        self.is_paused = False
        self.wait_manual = False
        self.waitingHumanMove = False
        self.currentMoveData = None
        
        self.startBtn.config(state="normal")
        self.pauseBtn.config(state="disabled", text="暂停")
        self.nextStepBtn.config(state="disabled")
        
        self.board = [['..' for _ in range(9)] for _ in range(10)]
        self.piece_positions = {}
        self.init_board()
        self.update_display()
        
        if self.lastMoveMarker:
            self.canvas.delete(self.lastMoveMarker)
            self.lastMoveMarker = None
        
        self.moveLabel.config(text="当前步数: 0")
        self.playerLabel.config(text="当前玩家: 红方")
        self.lastMoveLabel.config(text="最后一步: -")
        
        self.log_message("=== 游戏已重置 ===")
    
    def execute_move_step(self):
        if not self.currentMoveData:
            return
            
        mv, side, move_no, players = self.currentMoveData
        engine, opponent, player_name = players[side]
        
        self.log_message(f"{player_name}: {mv}")
        self.root.after(0, lambda m=mv: self.lastMoveLabel.config(text=f"最后一步: {m}"))
        
        pid, xs, ys = mv.split()
        x, y = int(xs), int(ys)
        
        if side == 0:  
            pid_move = pid
            xr, yr = x, y
        else:  
            mmv = self.mirror_move(mv)
            self.log_message(f"红方视角: {mmv}")
            pid_move, xs_m, ys_m = mmv.split()
            xr, yr = int(xs_m), int(ys_m)
        
        from_x, from_y = None, None
        if pid_move in self.piece_positions:
            from_x, from_y = self.piece_positions[pid_move]
        
        if pid_move in self.piece_positions:
            ox, oy = self.piece_positions[pid_move]
            self.board[oy][ox] = '..'
        self.piece_positions[pid_move] = (xr, yr)
        self.board[yr][xr] = pid_move
        
        self.root.after(0, self.update_display)
        
        if from_x is not None and from_y is not None:
            self.root.after(0, lambda: self.add_move_marker(from_x, from_y))
        
        opponent_move = self.reverse_mirror_move(mv)
        opponent.stdin.write(opponent_move + "\n")
        opponent.stdin.flush()
        
        self.currentMoveData = None

def main():
    root = tk.Tk()
    
    style = ttk.Style()
    style.theme_use('clam')
    
    app = XiangqiGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
