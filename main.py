import sys
import os
import re
import pronouncing
import colorsys
from collections import defaultdict
from functools import partial
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (QFont, QStandardItemModel, QStandardItem, 
                        QColor, QTextCharFormat, QSyntaxHighlighter,
                        QPalette)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QVBoxLayout, 
                           QWidget, QFileDialog, QMessageBox, QMenuBar, QAction,
                           QHBoxLayout, QTreeView)

def get_distinct_colors(n):
    """Generate n visually distinct colors using HSV color space"""
    if n <= 0:
        return []
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7
        value = 0.9
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append(QColor(int(r*255), int(g*255), int(b*255)))
    return colors

class RhymeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rhyme_groups = {}
        self.word_to_color = {}

    def set_rhyme_data(self, word_to_color):
        self.word_to_color = word_to_color
        self.rehighlight()

    def highlightBlock(self, text):
        for word, color in self.word_to_color.items():
            pattern = f"\\b{re.escape(word)}\\b"
            for match in re.finditer(pattern, text.lower()):
                start = match.start()
                length = match.end() - start
                format = QTextCharFormat()
                format.setBackground(color)
                self.setFormat(start, length, format)

class SimpleEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rhyme Text Editor")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create file explorer
        self.setup_file_explorer()
        main_layout.addWidget(self.file_explorer)
        
        # Create text editor
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont('Arial', 12))
        main_layout.addWidget(self.text_edit)
        
        # Set up rhyme highlighter
        self.highlighter = RhymeHighlighter(self.text_edit.document())
        
        # Create a timer for delayed rhyme processing
        self.rhyme_timer = QTimer()
        self.rhyme_timer.setSingleShot(True)
        self.rhyme_timer.timeout.connect(self.process_rhymes)
        
        # Connect text changed to timer
        self.text_edit.textChanged.connect(self.start_rhyme_timer)
        
        # Set the ratio between file explorer and text editor (1:4)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 4)
        
        # Create menu bar
        self.create_menu_bar()
        
        self.current_file = None

    def setup_file_explorer(self):
        self.file_explorer = QTreeView()
        self.file_model = QStandardItemModel()
        self.file_model.setHorizontalHeaderLabels(['Files'])
        self.file_explorer.setModel(self.file_model)
        
        # Set file explorer properties
        self.file_explorer.setMinimumWidth(200)
        self.file_explorer.setMaximumWidth(300)
        
        # Connect file explorer clicks
        self.file_explorer.clicked.connect(self.file_clicked)
        
        # Populate the file explorer
        self.refresh_file_explorer()

    def refresh_file_explorer(self):
        self.file_model.clear()
        self.file_model.setHorizontalHeaderLabels(['Files'])
        
        current_dir = os.getcwd()
        root_item = self.file_model.invisibleRootItem()
        
        try:
            for item in os.listdir(current_dir):
                path = os.path.join(current_dir, item)
                file_item = QStandardItem(item)
                file_item.setData(path, Qt.UserRole)
                
                # Icons
                if os.path.isdir(path):
                    file_item.setText(f"📁 {item}")
                else:
                    file_item.setText(f"📄 {item}")
                
                root_item.appendRow(file_item)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error reading directory: {str(e)}')

    def file_clicked(self, index):
        path = self.file_model.data(index, Qt.UserRole)
        if path and os.path.isfile(path):
            self.open_specific_file(path)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # New file
        new_action = QAction('New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        # Open file
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # Save file
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # Save As file
        save_as_action = QAction('Save As', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        # Refresh file explorer
        file_menu.addSeparator()
        refresh_action = QAction('Refresh File Explorer', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_file_explorer)
        file_menu.addAction(refresh_action)
        
        # Exit
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Options menu
        options_menu = menubar.addMenu('Options')
        
        # Dark Mode toggle
        dark_mode_action = QAction('Dark Mode', self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        options_menu.addAction(dark_mode_action)

    def toggle_dark_mode(self, enabled):
        app = QApplication.instance()
        if enabled:
            # Dark theme palette
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:
            # Light theme palette
            palette = app.style().standardPalette()
        
        app.setPalette(palette)

    def new_file(self):
        if self.maybe_save():
            self.text_edit.clear()
            self.current_file = None
            self.setWindowTitle("Rhyme Text Editor - Untitled")

    def open_file(self):
        if self.maybe_save():
            fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                 'Text files (*.txt);;All files (*.*)')
            if fname:
                self.open_specific_file(fname)

    def open_specific_file(self, fname):
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                self.text_edit.setText(f.read())
            self.current_file = fname
            self.setWindowTitle(f"Rhyme Text Editor - {os.path.basename(fname)}")
            self.text_edit.document().setModified(False)
        except Exception as e:
            QMessageBox.warning(self, 'Error',
                              f'Could not open file: {str(e)}')

    def save_file(self):
        if self.current_file:
            return self.save_specific_file(self.current_file)
        return self.save_file_as()

    def save_file_as(self):
        fname, _ = QFileDialog.getSaveFileName(self, 'Save file', '',
                                             'Text files (*.txt);;All files (*.*)')
        if fname:
            return self.save_specific_file(fname)
        return False

    def save_specific_file(self, fname):
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            self.current_file = fname
            self.setWindowTitle(f"Rhyme Text Editor - {os.path.basename(fname)}")
            self.text_edit.document().setModified(False)
            self.refresh_file_explorer()
            return True
        except Exception as e:
            QMessageBox.warning(self, 'Error',
                              f'Could not save file: {str(e)}')
            return False

    def start_rhyme_timer(self):
        self.rhyme_timer.start(500)

    def get_rhyme_groups(self, words):
        """Group words by their rhyming parts"""
        rhyme_dict = defaultdict(list)
        
        for word in words:
            clean_word = word.lower().strip()
            if not clean_word or len(clean_word) < 3:  # Skip short words
                continue
                
            try:
                pronunciations = pronouncing.phones_for_word(clean_word)
                if pronunciations:
                    rhyme_part = pronouncing.rhyming_part(pronunciations[0])
                    if rhyme_part:
                        rhyme_dict[rhyme_part].append(clean_word)
            except Exception:
                continue
        
        return {k: v for k, v in rhyme_dict.items() if len(v) > 1}

    def process_rhymes(self):
        try:
            current_text = self.text_edit.toPlainText()
            
            # Collect all words
            words = re.findall(r'\b\w+\b', current_text.lower())
            
            # Get rhyme groups
            rhyme_groups = self.get_rhyme_groups(words)
            
            # Generate colors for each rhyme group
            colors = get_distinct_colors(len(rhyme_groups))
            
            # Create word to color mapping
            word_to_color = {}
            for i, (_, words) in enumerate(rhyme_groups.items()):
                if i < len(colors):  # Safety check
                    for word in words:
                        word_to_color[word] = colors[i]
            
            # Update the highlighter
            self.highlighter.set_rhyme_data(word_to_color)
            
        except Exception as e:
            print(f"Error processing rhymes: {e}")

    def maybe_save(self):
        if self.text_edit.document().isModified():
            reply = QMessageBox.question(self, 'Save Changes?',
                                       'Do you want to save your changes?',
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                return self.save_file()
            elif reply == QMessageBox.Cancel:
                return False
            return True
        return True

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        editor = SimpleEditor()
        editor.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error: {e}")