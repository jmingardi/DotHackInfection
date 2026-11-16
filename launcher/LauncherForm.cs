using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace DotHackInfection
{
    internal sealed class BindDialog : Form
    {
        internal int Input=-1;
        [DllImport("user32.dll")] static extern short GetAsyncKeyState(int key);
        internal BindDialog(string action)
        {
            Text="Bind "+action; ClientSize=new Size(460,220); StartPosition=FormStartPosition.CenterParent;
            FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=false; MinimizeBox=false; KeyPreview=true;
            BackColor=Color.FromArgb(24,29,39); ForeColor=Color.White; Font=new Font("Segoe UI",10);
            var label=new Label {Text="Press a key for "+action+".\nClick inside the box to bind a mouse button.",Dock=DockStyle.Top,Height=65,Padding=new Padding(18,14,10,0)};
            var capture=new Panel {BackColor=Color.FromArgb(37,45,58),Location=new Point(18,80),Size=new Size(424,64),TabStop=true};
            capture.Controls.Add(new Label {Text="KEY / MOUSE CAPTURE",ForeColor=Color.LightGray,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleCenter,Enabled=false});
            capture.MouseDown+=(s,e)=>{int code=e.Button==MouseButtons.Left?1000:e.Button==MouseButtons.Middle?1001:e.Button==MouseButtons.Right?1002:e.Button==MouseButtons.XButton1?1003:1004;Accept(code);};
            capture.MouseWheel+=(s,e)=>Accept(e.Delta>0?1010:1011);
            var cancel=new Button {Text="Cancel",Location=new Point(342,168),Size=new Size(100,32),DialogResult=DialogResult.Cancel};
            var clear=new Button {Text="Unbind",Location=new Point(18,168),Size=new Size(100,32)};
            clear.Click+=(s,e)=>Accept(0);
            Controls.AddRange(new Control[]{label,capture,cancel,clear});
            KeyDown+=(s,e)=>{ e.SuppressKeyPress=true; string name=KeyName(e.KeyCode); if(name!=null){int code=Native.SDL_GetScancodeFromName(Native.Utf8(name)); if(code>0) Accept(code);} };
            Shown+=(s,e)=>capture.Focus();
        }
        void Accept(int code) { Input=code; DialogResult=DialogResult.OK; Close(); }
        static string KeyName(Keys key)
        {
            if(key>=Keys.A && key<=Keys.Z) return key.ToString();
            if(key>=Keys.D0 && key<=Keys.D9) return ((int)key-(int)Keys.D0).ToString();
            if(key>=Keys.NumPad0 && key<=Keys.NumPad9) return "Keypad "+((int)key-(int)Keys.NumPad0);
            if(key>=Keys.F1 && key<=Keys.F24) return key.ToString();
            switch(key) {
                case Keys.Return:return "Return"; case Keys.Space:return "Space"; case Keys.Escape:return "Escape";
                case Keys.Up:return "Up"; case Keys.Down:return "Down"; case Keys.Left:return "Left"; case Keys.Right:return "Right";
                case Keys.Tab:return "Tab"; case Keys.Back:return "Backspace"; case Keys.Delete:return "Delete";
                case Keys.Insert:return "Insert"; case Keys.Home:return "Home"; case Keys.End:return "End";
                case Keys.PageUp:return "PageUp"; case Keys.PageDown:return "PageDown"; case Keys.CapsLock:return "CapsLock";
                case Keys.ShiftKey:return GetAsyncKeyState(0xA1)<0?"Right Shift":"Left Shift";
                case Keys.ControlKey:return GetAsyncKeyState(0xA3)<0?"Right Ctrl":"Left Ctrl";
                case Keys.Menu:return GetAsyncKeyState(0xA5)<0?"Right Alt":"Left Alt";
                case Keys.OemMinus:return "-"; case Keys.Oemplus:return "="; case Keys.Oemcomma:return ",";
                case Keys.OemPeriod:return "."; case Keys.OemQuestion:return "/"; case Keys.OemSemicolon:return ";";
                case Keys.OemQuotes:return "'"; case Keys.OemOpenBrackets:return "["; case Keys.OemCloseBrackets:return "]";
                case Keys.OemPipe:return "\\"; case Keys.Oemtilde:return "`";
                case Keys.Multiply:return "Keypad *"; case Keys.Add:return "Keypad +";
                case Keys.Subtract:return "Keypad -"; case Keys.Divide:return "Keypad /"; case Keys.Decimal:return "Keypad .";
            }
            return null;
        }
    }

    internal sealed class LauncherForm : Form
    {
        static readonly Color Background=Color.FromArgb(15,20,29),PanelColor=Color.FromArgb(24,31,43),Field=Color.FromArgb(33,42,56),Accent=Color.FromArgb(246,188,83),Muted=Color.FromArgb(170,183,201);
        readonly Profile profile;
        readonly int qaFrames;
        readonly TabControl tabs=new TabControl();
        readonly TextBox iso=new TextBox();
        readonly Label discStatus=new Label(),status=new Label(),controllers=new Label();
        readonly ProgressBar progress=new ProgressBar();
        readonly Button play=new Button(),save=new Button(),browse=new Button(),reload=new Button();
        readonly ComboBox display=new ComboBox(),scale=new ComboBox(),look=new ComboBox(),sharp=new ComboBox();
        readonly DataGridView grid=new DataGridView();
        BackgroundWorker verifier;
        string draftKeys,verifiedPath,lastLog="";
        long verifiedLength,verifiedWrite;
        bool refreshing,closing,gameRunning;
        Process child;
        StreamWriter gameLog;
        readonly object logLock=new object();
        static readonly string[] Actions={"D-pad Up","D-pad Down","D-pad Left","D-pad Right","Left stick Up / walk","Left stick Down / walk","Left stick Left / walk","Left stick Right / walk","Right stick Up","Right stick Down","Right stick Left","Right stick Right","Cross","Circle","Square","Triangle","L1","R1","L2","R2","L3","R3","Start","Select","Right-stick modifier","Both stick buttons","Key card","Quick menu"};
        internal LauncherForm(Profile profile,int frames)
        {
            this.profile=profile;qaFrames=frames;
            Text=".hack//INFECTION - Launcher"; Name="DotHackLauncher";
            ClientSize=new Size(980,680); MinimumSize=new Size(820,600); StartPosition=FormStartPosition.CenterScreen;
            Font=new Font("Segoe UI",10); AutoScaleMode=AutoScaleMode.Dpi; BackColor=Background; ForeColor=Color.White;
            var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,Padding=new Padding(24)};
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute,86));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,38));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,54));
            var header=new Panel {Dock=DockStyle.Fill};
            header.Controls.Add(new Label {Text=".hack//INFECTION",Font=new Font("Segoe UI",26,FontStyle.Bold),AutoSize=true,Location=new Point(0,0)});
            header.Controls.Add(new Label {Text="EXPERIMENTAL  /  WINDOWS X64  /  SLUS-20267",ForeColor=Muted,AutoSize=true,Location=new Point(3,49)});
            layout.Controls.Add(header,0,0);
            tabs.Dock=DockStyle.Fill; tabs.Name="LauncherTabs"; layout.Controls.Add(tabs,0,1);
            MakeHome();MakeDisplay();MakeControls();
            status.Dock=DockStyle.Fill;status.TextAlign=ContentAlignment.MiddleLeft;status.ForeColor=Muted;status.Name="LauncherStatus";layout.Controls.Add(status,0,2);
            var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=4};
            footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,148));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,154));
            var log=Button("Open last log","OpenLog",(s,e)=>{if(File.Exists(lastLog))Process.Start(new ProcessStartInfo(lastLog){UseShellExecute=true});else status.Text="A log is created when you start the game.";});
            log.Width=130;footer.Controls.Add(log,0,0);
            StyleButton(reload,"Reload","ReloadSettings");reload.Click+=(s,e)=>LoadSettings();footer.Controls.Add(reload,1,0);
            StyleButton(save,"Save settings","SaveSettings");save.Click+=(s,e)=>{try{SaveSettings();status.Text="Settings saved.";}catch(Exception error){Error(error.Message);}};footer.Controls.Add(save,2,0);
            StyleButton(play,"Play","PlayGame");play.BackColor=Accent;play.ForeColor=Color.FromArgb(22,24,29);play.Font=new Font(Font,FontStyle.Bold);play.Enabled=false;play.Click+=(s,e)=>Play();footer.Controls.Add(play,3,0);
            layout.Controls.Add(footer,0,3);Controls.Add(layout);
            Shown+=(s,e)=>{LoadSettings();RefreshControllers();};
            FormClosing+=(s,e)=>{if(gameRunning){e.Cancel=true;WindowState=FormWindowState.Minimized;return;}closing=true;if(verifier!=null&&verifier.IsBusy)verifier.CancelAsync();};
        }
        static void StyleButton(Button button,string text,string name)
        {button.Text=text;button.Name=name;button.AccessibleName=text;button.AccessibleRole=AccessibleRole.PushButton;button.Dock=DockStyle.Fill;button.Margin=new Padding(4,7,4,7);button.FlatStyle=FlatStyle.Flat;button.FlatAppearance.BorderColor=Color.FromArgb(74,88,107);button.BackColor=Field;button.ForeColor=Color.White;button.Cursor=Cursors.Hand;}
        static Button Button(string text,string name,EventHandler handler)
        {var b=new Button();StyleButton(b,text,name);b.Click+=handler;return b;}
        TabPage Page(string text)
        {var page=new TabPage(text){BackColor=PanelColor,ForeColor=Color.White,Padding=new Padding(20)};tabs.TabPages.Add(page);return page;}
        static Label Label(string text,int height)
        {return new Label {Text=text,Height=height,Dock=DockStyle.Top,ForeColor=Muted,AutoEllipsis=true};}
        void MakeHome()
        {
            var page=Page("Game");
            var content=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=6};
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
            content.RowStyles.Add(new RowStyle(SizeType.Absolute,34));content.RowStyles.Add(new RowStyle(SizeType.Absolute,48));content.RowStyles.Add(new RowStyle(SizeType.Absolute,48));content.RowStyles.Add(new RowStyle(SizeType.Absolute,20));content.RowStyles.Add(new RowStyle(SizeType.Percent,100));content.RowStyles.Add(new RowStyle(SizeType.Absolute,56));
            content.Controls.Add(new Label {Text="Your game image",Font=new Font(Font,FontStyle.Bold),Dock=DockStyle.Fill},0,0);
            var picker=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2};picker.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));picker.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));
            iso.Name="IsoPath";iso.AccessibleName="IsoPath";iso.ReadOnly=true;iso.Dock=DockStyle.Fill;iso.Margin=new Padding(0,8,8,0);iso.BackColor=Field;iso.ForeColor=Color.White;picker.Controls.Add(iso,0,0);
            StyleButton(browse,"Browse...","BrowseIso");browse.Click+=(s,e)=>{using(var dialog=new OpenFileDialog {Filter="PlayStation 2 ISO (*.iso)|*.iso",Title="Select .hack//INFECTION (USA)",CheckFileExists=true})if(dialog.ShowDialog(this)==DialogResult.OK){iso.Text=dialog.FileName;VerifyImage();}};picker.Controls.Add(browse,1,0);content.Controls.Add(picker,0,1);
            discStatus.Dock=DockStyle.Fill;discStatus.ForeColor=Muted;discStatus.Name="DiscStatus";content.Controls.Add(discStatus,0,2);
            progress.Dock=DockStyle.Fill;progress.Margin=new Padding(0,0,0,4);progress.Visible=false;progress.Name="DiscProgress";content.Controls.Add(progress,0,3);
            var hints=new Label {Text="Choose your own USA SLUS-20267 ISO. The game image is read in place.\n\nF1 opens the in-game menu. F11 toggles fullscreen.\nYour existing memory card and preferences are kept in the same saves folder.\n\nNew areas can briefly pause while additional code is compiled.",ForeColor=Muted,Dock=DockStyle.Fill,Padding=new Padding(0,18,0,0)};content.Controls.Add(hints,0,4);
            var folders=new FlowLayoutPanel {Dock=DockStyle.Fill};
            var open=Button("Open saves folder","OpenSaves",(s,e)=>{Directory.CreateDirectory(profile.DirectoryPath);Process.Start(new ProcessStartInfo(profile.DirectoryPath){UseShellExecute=true});});open.Dock=DockStyle.None;open.Size=new Size(180,38);folders.Controls.Add(open);content.Controls.Add(folders,0,5);page.Controls.Add(content);
        }
        void MakeDisplay()
        {
            var page=Page("Display");var table=new TableLayoutPanel {Dock=DockStyle.Top,ColumnCount=2,AutoSize=true};
            table.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,225));table.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
            AddOption(table,"Window mode",display,"DisplayMode",new[]{"Windowed","Borderless fullscreen"});
            AddOption(table,"Internal resolution",scale,"InternalResolution",new[]{"Native (1x)","2x","3x","4x"});
            AddOption(table,"Picture filter",look,"PictureFilter",new[]{"Crisp","Crisp + smooth edges","Soft","Soft + smooth edges","Sharp","Sharp + smooth edges"});
            AddOption(table,"Text / menu filtering",sharp,"ArtFilter",new[]{"Soft","Sharp","Sharpest"});
            var note=Label("Original 4:3 presentation and game timing are preserved.\nHigher internal resolutions require more GPU memory and processing power.\nF1 picture settings remain available during play.",95);note.Padding=new Padding(0,20,0,0);note.Dock=DockStyle.Bottom;page.Controls.Add(table);page.Controls.Add(note);
        }
        static void AddOption(TableLayoutPanel table,string label,ComboBox box,string name,string[] values)
        {int row=table.RowCount++;table.RowStyles.Add(new RowStyle(SizeType.Absolute,55));table.Controls.Add(new Label {Text=label,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft},0,row);box.Name=name;box.AccessibleName=name;box.DropDownStyle=ComboBoxStyle.DropDownList;box.Items.AddRange(values);box.Dock=DockStyle.Fill;box.Margin=new Padding(0,12,0,8);table.Controls.Add(box,1,row);}
        void MakeControls()
        {
            var page=Page("Controls");var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4};
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute,42));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,48));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,54));
            layout.Controls.Add(Label("Click Bind to capture a key or mouse button. Edit a binding to enter comma-separated alternatives.",42),0,0);
            grid.Name="KeyBindings";grid.Text="Keyboard and mouse bindings";grid.AccessibleName=grid.Text;grid.AccessibleRole=AccessibleRole.Table;grid.Dock=DockStyle.Fill;grid.BackgroundColor=Field;grid.BorderStyle=BorderStyle.None;
            grid.AllowUserToAddRows=false;grid.AllowUserToDeleteRows=false;grid.AllowUserToResizeRows=false;grid.RowHeadersVisible=false;grid.AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill;
            grid.DefaultCellStyle.BackColor=Field;grid.DefaultCellStyle.ForeColor=Color.White;grid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(62,77,98);grid.DefaultCellStyle.SelectionForeColor=Color.White;grid.RowTemplate.Height=31;grid.EnableHeadersVisualStyles=false;grid.ColumnHeadersDefaultCellStyle.BackColor=PanelColor;grid.ColumnHeadersDefaultCellStyle.ForeColor=Muted;
            grid.Columns.Add(new DataGridViewTextBoxColumn {Name="Action",HeaderText="Controller input",ReadOnly=true,FillWeight=42});
            grid.Columns.Add(new DataGridViewTextBoxColumn {Name="Binding",HeaderText="Keyboard / mouse",FillWeight=48});
            grid.Columns.Add(new DataGridViewButtonColumn {Name="Capture",HeaderText="",Text="Bind",UseColumnTextForButtonValue=true,FillWeight=16});
            grid.CellContentClick+=(s,e)=>{if(e.RowIndex>=0&&e.ColumnIndex==2)CaptureBinding(e.RowIndex);};
            grid.CellValidating+=(s,e)=>{if(refreshing||e.RowIndex<0||e.ColumnIndex!=1||!grid.IsCurrentCellDirty)return;try{draftKeys=Native.SetBinding(draftKeys,e.RowIndex,Convert.ToString(e.FormattedValue));grid.Rows[e.RowIndex].ErrorText="";status.Text="Controls changed. Save settings or Play to apply.";}catch(Exception error){e.Cancel=true;grid.Rows[e.RowIndex].ErrorText=error.Message;status.Text=error.Message;}};
            layout.Controls.Add(grid,0,1);
            var tools=new FlowLayoutPanel {Dock=DockStyle.Fill};
            var reset=Button("Reset keyboard bindings","ResetBindings",(s,e)=>{draftKeys=Native.Reset(draftKeys);RefreshBindings();status.Text="Default bindings selected. Save settings or Play to apply.";});reset.Dock=DockStyle.None;reset.Size=new Size(220,34);tools.Controls.Add(reset);
            var refresh=Button("Refresh controllers","RefreshControllers",(s,e)=>RefreshControllers());refresh.Dock=DockStyle.None;refresh.Size=new Size(180,34);tools.Controls.Add(refresh);layout.Controls.Add(tools,0,2);
            controllers.Dock=DockStyle.Fill;controllers.ForeColor=Muted;controllers.Name="Controllers";controllers.Text="Controllers use their standard PS2 layout and connect automatically.";layout.Controls.Add(controllers,0,3);page.Controls.Add(layout);
        }
        void RefreshControllers(){try{controllers.Text=Native.Controllers()+"\nControllers connect automatically; keyboard and mouse stay available.";}catch(Exception error){controllers.Text=error.Message;}}
        void LoadSettings()
        {
            try {
                profile.Reload();draftKeys=profile.KeysText;RefreshBindings();var values=Native.Values(draftKeys);
                look.SelectedIndex=Int32.Parse(values["look"]);scale.SelectedIndex=Int32.Parse(values["scale"])-1;sharp.SelectedIndex=Int32.Parse(values["sharp"]);
                display.SelectedIndex=profile.Settings.Fullscreen?1:0;
                string path=profile.Settings.IsoPath;
                if(String.IsNullOrEmpty(path))path=Path.Combine(Runtime.Root,"Dot Hack Part 1 - Infection (USA).iso");
                iso.Text=path;status.Text="Settings loaded. F1 remains available during play.";
                if(!String.Equals(path,verifiedPath,StringComparison.OrdinalIgnoreCase))VerifyImage();
            } catch(Exception error){Error(error.Message);}
        }
        void RefreshBindings()
        {int row=grid.CurrentCell==null?0:grid.CurrentCell.RowIndex;int column=grid.CurrentCell==null?0:grid.CurrentCell.ColumnIndex;int first=grid.FirstDisplayedScrollingRowIndex;
            refreshing=true;try{var values=Native.Values(draftKeys);grid.Rows.Clear();for(int i=0;i<Actions.Length;++i)grid.Rows.Add(Actions[i],values[i.ToString()]);
                grid.CurrentCell=grid.Rows[Math.Min(row,grid.Rows.Count-1)].Cells[column];if(first>=0)grid.FirstDisplayedScrollingRowIndex=first;
            }finally{refreshing=false;}}
        void CaptureBinding(int row)
        {
            using(var dialog=new BindDialog(Actions[row]))if(dialog.ShowDialog(this)==DialogResult.OK)
                try{draftKeys=dialog.Input==0?Native.SetBinding(draftKeys,row,"none"):Native.Bind(draftKeys,row,dialog.Input);RefreshBindings();status.Text="Controls changed. Save settings or Play to apply.";}catch(Exception error){Error(error.Message);}
        }
        void VerifyImage()
        {
            if(verifier!=null&&verifier.IsBusy){status.Text="Disc verification is already running.";return;}
            verifiedPath=null;play.Enabled=false;progress.Value=0;progress.Visible=true;browse.Enabled=false;
            discStatus.Text="Checking your ISO...";string path=iso.Text;long length=0,write=0;
            verifier=new BackgroundWorker {WorkerReportsProgress=true,WorkerSupportsCancellation=true};
            verifier.DoWork+=(s,e)=>{Runtime.VerifyIso(path,p=>verifier.ReportProgress(p),()=>verifier.CancellationPending);var info=new FileInfo(path);length=info.Length;write=info.LastWriteTimeUtc.Ticks;e.Result=path;};
            verifier.ProgressChanged+=(s,e)=>{if(!closing){progress.Value=e.ProgressPercentage;discStatus.Text="Verifying supported disc: "+e.ProgressPercentage+"%";}};
            verifier.RunWorkerCompleted+=(s,e)=>{if(closing)return;browse.Enabled=true;progress.Visible=false;
                if(e.Error!=null){discStatus.ForeColor=Color.FromArgb(255,168,145);discStatus.Text=e.Error.Message;return;}
                if(e.Cancelled)return;verifiedPath=(string)e.Result;verifiedLength=length;verifiedWrite=write;discStatus.ForeColor=Color.FromArgb(151,222,183);discStatus.Text="Verified: .hack//INFECTION (USA), SLUS-20267";play.Enabled=!gameRunning;};
            verifier.RunWorkerAsync();
        }
        void SaveSettings()
        {if(!grid.EndEdit())throw new InvalidDataException("Finish editing the highlighted binding first.");draftKeys=Native.Options(draftKeys,look.SelectedIndex,scale.SelectedIndex+1,sharp.SelectedIndex);profile.Save(draftKeys,iso.Text,display.SelectedIndex==1);}
        void Error(string message){status.Text=message;MessageBox.Show(this,message,".hack//INFECTION",MessageBoxButtons.OK,MessageBoxIcon.Warning);}
        void Play()
        {
            try {
                if(gameRunning)return;
                if(verifiedPath==null){VerifyImage();return;}
                var file=new FileInfo(verifiedPath);
                if(!file.Exists||file.Length!=verifiedLength||file.LastWriteTimeUtc.Ticks!=verifiedWrite){VerifyImage();return;}
                foreach(Process process in Process.GetProcessesByName("ps2run"))using(process)
                    if(String.Equals(process.MainModule.FileName,Runtime.Executable,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("The game is already running. Close it before starting another session.");
                SaveSettings();Runtime.ImportCompletedCaches();
                string logs=Path.Combine(profile.DirectoryPath,"launcher-logs");Directory.CreateDirectory(logs);
                lastLog=Path.Combine(logs,DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff")+".log");
                gameLog=new StreamWriter(lastLog,false,new UTF8Encoding(false)){AutoFlush=true};
                var info=Runtime.StartInfo(verifiedPath,profile,display.SelectedIndex==1,qaFrames);
                gameLog.WriteLine(".hack//INFECTION graphical launcher\n"+info.FileName+" "+info.Arguments);
                child=new Process {StartInfo=info,EnableRaisingEvents=true};
                child.OutputDataReceived+=LogLine;child.ErrorDataReceived+=LogLine;
                child.Exited+=(s,e)=>{Process exited=(Process)s;exited.WaitForExit();int code=exited.ExitCode;lock(logLock){if(gameLog!=null){gameLog.WriteLine("Game exit code: "+code);gameLog.Dispose();gameLog=null;}}
                    if(!IsDisposed)BeginInvoke((Action)(()=>{gameRunning=false;tabs.Enabled=true;save.Enabled=true;reload.Enabled=true;play.Enabled=verifiedPath!=null;WindowState=FormWindowState.Normal;Show();Activate();LoadSettings();status.Text=code==0?"Game closed. Your saves and settings are ready for next time.":"Game exited with code "+code+". Open last log for details.";exited.Dispose();child=null;}));};
                gameRunning=true;tabs.Enabled=false;save.Enabled=false;reload.Enabled=false;play.Enabled=false;
                if(!child.Start())throw new InvalidOperationException("The game could not start.");
                child.BeginOutputReadLine();child.BeginErrorReadLine();status.Text="Game running...";WindowState=FormWindowState.Minimized;
            } catch(Exception error){gameRunning=false;tabs.Enabled=true;save.Enabled=true;reload.Enabled=true;play.Enabled=verifiedPath!=null;lock(logLock){if(gameLog!=null){gameLog.Dispose();gameLog=null;}}Error(error.Message);}
        }
        void LogLine(object sender,DataReceivedEventArgs e){if(e.Data==null)return;lock(logLock){if(gameLog!=null)gameLog.WriteLine(e.Data);}}
    }

    internal static class Program
    {
        [STAThread] static int Main(string[] args)
        {
            string profile=Path.Combine(Runtime.Root,"saves");int frames=0;bool selfTest=false;
            try {
                for(int i=0;i<args.Length;++i) {
                    if(args[i]=="--profile-dir"&&i+1<args.Length)profile=Path.GetFullPath(args[++i]);
                    else if(args[i]=="--qa-frames"&&i+1<args.Length)frames=Int32.Parse(args[++i]);
                    else if(args[i]=="--self-test")selfTest=true;
                    else throw new ArgumentException("Unknown launcher argument: "+args[i]);
                }
                if((frames!=0||selfTest)&&(!Path.GetFullPath(profile).StartsWith(Path.Combine(Runtime.Root,"evidence")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||frames<0||frames>3600))
                    throw new ArgumentException("Launcher QA requires an isolated evidence profile and at most 3600 frames.");
                Native.SetDllDirectory(Path.Combine(Runtime.Root,"launcher-bin"));
                if(selfTest){SelfTest.Run(profile);return 0;}
                using(var mutex=new Mutex(false,"Local\\DotHackInfectionLauncher_"+Fingerprint(profile))) {
                    bool owned=false;try{owned=mutex.WaitOne(0);}catch(AbandonedMutexException){owned=true;}
                    if(!owned){MessageBox.Show("The launcher is already open for this profile.",".hack//INFECTION");return 0;}
                    try{Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new LauncherForm(new Profile(profile),frames));}
                    finally{mutex.ReleaseMutex();}
                }
                return 0;
            } catch(Exception error){
                if(selfTest){try{if(Path.GetFullPath(profile).StartsWith(Path.Combine(Runtime.Root,"evidence")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)){Directory.CreateDirectory(profile);File.WriteAllText(Path.Combine(profile,"self-test-error.txt"),error.ToString());}}catch{}return 1;}
                MessageBox.Show(error.Message,".hack//INFECTION launcher",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;
            }
        }
        static string Fingerprint(string text){using(var hash=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(text.ToLowerInvariant()))).Replace("-","").Substring(0,24);}
    }
}
