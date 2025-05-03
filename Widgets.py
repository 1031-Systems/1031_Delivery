# Import local version of PyQt, either 5 or 6
usedPyQt = None
try:
    # PyQt5 import block for all widgets
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtPrintSupport import *
    usedPyQt = 5
except:
    try:
        # PyQt6 import block for all widgets
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *
        from PyQt6.QtPrintSupport import *
        usedPyQt = 6
    except:
        sys.stderr.write('Whoops - Unable to find PyQt5 or PyQt6 - Quitting\n')
        exit(10)


#####################################################################
class TextDisplayDialog(QDialog):
    """
    Class: TextDisplayDialog
        Derives from: (QDialog)

    The TextDisplayDialog class is a popup window that displays text
    from a string or a file.
    ...
    Attributes
    ----------
    name : str
        Title of window
    textView : QTextBrowser

    Methods
    -------
    setText(self, text)
    setSource(self, instr)
    """

    def __init__(self,
        name,
        text='',
        parent=None,
        ):
        super(TextDisplayDialog, self).__init__(parent)

        self.name = name
        self.textView = QTextBrowser(self)
        self.textView.setPlainText(text)
        self.textView.setReadOnly(True)
        self.resize(500, 600)
        # Add shortcut to open searchbar
        taction = QAction('', self, shortcut=QKeySequence("Ctrl+F"),
            triggered=self.showFinder)
        self.addAction(taction)
        # Add shortcut to close window
        taction = QAction('', self, shortcut=QKeySequence("Ctrl+W"),
            triggered=self.accept)
        self.addAction(taction)
        # Add print capability
        taction = QAction('', self, shortcut=QKeySequence("Ctrl+P"),
            triggered=self.print)
        self.addAction(taction)

        # Save lower-case version of text for various searches
        self.text = self.textView.document().toPlainText().lower()

        layout = QFormLayout()
        self.setLayout(layout)
        layout.addRow(self.textView)

        # Text find tool for searches within window
        tlayout = QHBoxLayout()
        self.findWidget = QWidget()
        self.findWidget.hide()
        layout.addRow(self.findWidget)

        # Widget for entering search text
        self.searchTextWidget = QLineEdit()
        tlayout.addWidget(self.searchTextWidget)

        # Not sure why but whichever of these two buttons has focus also gets connected to
        # returnPressed in the QLineEdit so return always initiates another search.  Handy.
        # Because the Down arrow is inserted first, it has focus by default so return does
        # a forward search.  Clicking the up arrow does a backward search and sets focus
        # so subsequent returns continue searching backwards.
        tbutt = QPushButton()
        tbutt.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarUnshadeButton))  #ArrowDown))
        tbutt.clicked.connect(self.findForwards)
        tlayout.addWidget(tbutt)
        tbutt = QPushButton()
        tbutt.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton))  #ArrowUp))
        tbutt.clicked.connect(self.findBackwards)
        tlayout.addWidget(tbutt)
        self.findWidget.setLayout(tlayout)

    def showFinder(self):
        self.findWidget.setVisible(not self.findWidget.isVisible())
        # Set focus to text widget so user can start typing immediately
        self.searchTextWidget.setFocus()

    def findForwards(self):
        txt = self.searchTextWidget.text()
        if len(txt) > 0:
            if self.text.find(txt.lower()) < 0: return
            flag = self.textView.find(txt)
            if not flag:
                # Go to beginning and try again
                self.textView.moveCursor(QTextCursor.MoveOperation.Start)
                flag = self.textView.find(txt)

    def findBackwards(self):
        txt = self.searchTextWidget.text()
        if len(txt) > 0:
            if self.text.find(txt.lower()) < 0: return
            flag = self.textView.find(txt, QTextDocument.FindFlag.FindBackward)
            if not flag:
                # Go to end and try again
                self.textView.moveCursor(QTextCursor.MoveOperation.End)
                flag = self.textView.find(txt, QTextDocument.FindFlag.FindBackward)

    def print(self):
        printDialog = QPrintDialog()
        result = printDialog.exec ()
        if (result == QDialog.DialogCode.Accepted):
            result = printDialog.printer ()
            self.textView.print (result)


    def setText(self, text):
        """
        The method setText sets the displayed text to the incoming text
            member of class: TextDisplayDialog
        Parameters
        ----------
        self : TextDisplayDialog
        text : str
            The text to be displayed
        """
        self.textView.setPlainText(text)
        # Save lower-case version of text for various searches
        self.text = self.textView.document().toPlainText().lower()

    def setMarkdown(self, text):
        """
        The method setMarkdown sets the displayed text to the incoming Markdown
            member of class: TextDisplayDialog
        Parameters
        ----------
        self : TextDisplayDialog
        text : str
            The Markdown to be displayed
        """
        self.textView.setMarkdown(text)
        # Save lower-case version of text for various searches
        self.text = self.textView.document().toPlainText().lower()


    def setSource(self, instr):
        """
        The method setSource sets the displayed text from the
        specified local file.
            member of class: TextDisplayDialog
        Parameters
        ----------
        self : TextDisplayDialog
        instr : Path to local file
        """
        self.textView.setSource(QUrl.fromLocalFile(instr))
        # Save lower-case version of text for various searches
        self.text = self.textView.document().toPlainText().lower()

