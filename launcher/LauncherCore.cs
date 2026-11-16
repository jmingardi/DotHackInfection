using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace DotHackInfection
{
    internal static class Native
    {
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] internal static extern bool SetDllDirectory(string path);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_defaults();
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_error();
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_validate(byte[] text);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_values(byte[] text);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_bind(byte[] text, int action, int input);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_set_binding(byte[] text, int action, byte[] value);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_options(byte[] text, int look, int scale, int sharp);
        [DllImport("dh_controls.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr dh_reset(byte[] text);
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern int SDL_GetScancodeFromName(byte[] text);
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern int SDL_InitSubSystem(uint flags);
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern void SDL_QuitSubSystem(uint flags);
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern void SDL_PumpEvents();
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern int SDL_NumJoysticks();
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] internal static extern int SDL_IsGameController(int index);
        [DllImport("SDL2.dll", CallingConvention=CallingConvention.Cdecl)] static extern IntPtr SDL_GameControllerNameForIndex(int index);
        internal static byte[] Utf8(string text) { return Encoding.UTF8.GetBytes(text + "\0"); }
        internal static string Text(IntPtr value)
        {
            if (value == IntPtr.Zero) throw new InvalidOperationException(Text(dh_error()));
            int length=0;
            while (Marshal.ReadByte(value,length)!=0) ++length;
            byte[] bytes=new byte[length]; Marshal.Copy(value,bytes,0,length);
            return Encoding.UTF8.GetString(bytes);
        }
        internal static string Defaults() { return Text(dh_defaults()); }
        internal static string Validate(string text) { return Text(dh_validate(Utf8(text))); }
        internal static string Bind(string text,int action,int input) { return Text(dh_bind(Utf8(text),action,input)); }
        internal static string SetBinding(string text,int action,string value) { return Text(dh_set_binding(Utf8(text),action,Utf8(value))); }
        internal static string Options(string text,int look,int scale,int sharp) { return Text(dh_options(Utf8(text),look,scale,sharp)); }
        internal static string Reset(string text) { return Text(dh_reset(Utf8(text))); }
        internal static Dictionary<string,string> Values(string text)
        {
            var values=new Dictionary<string,string>();
            foreach(string row in Text(dh_values(Utf8(text))).Split('\n'))
            { int tab=row.IndexOf('\t'); if(tab>0) values[row.Substring(0,tab)]=row.Substring(tab+1); }
            return values;
        }
        internal static string Controllers()
        {
            if(SDL_InitSubSystem(0x2000)!=0) return "Controller detection unavailable. Keyboard and mouse remain available.";
            try {
                SDL_PumpEvents(); var names=new List<string>();
                for(int i=0;i<SDL_NumJoysticks();++i)
                    if(SDL_IsGameController(i)!=0) names.Add(Text(SDL_GameControllerNameForIndex(i)));
                return names.Count==0 ? "No controller detected. Connect an SDL-compatible controller, then refresh."
                    : "Connected: "+String.Join(", ",names.ToArray());
            } finally { SDL_QuitSubSystem(0x2000); }
        }
    }

    public sealed class Preferences
    {
        public string IsoPath="";
        public bool Fullscreen=false;
    }

    internal sealed class Profile
    {
        internal readonly string DirectoryPath, KeysPath, PreferencesPath;
        internal string LoadedKeys;
        internal Preferences Settings;
        internal Profile(string directory)
        {
            DirectoryPath=Path.GetFullPath(directory);
            KeysPath=Path.Combine(DirectoryPath,"keys.ini");
            PreferencesPath=Path.Combine(DirectoryPath,"launcher.json");
            Reload();
        }
        internal void Reload()
        {
            LoadedKeys=File.Exists(KeysPath)?File.ReadAllText(KeysPath,Encoding.UTF8):null;
            Settings=File.Exists(PreferencesPath)
                ? new JavaScriptSerializer().Deserialize<Preferences>(File.ReadAllText(PreferencesPath,Encoding.UTF8))
                : new Preferences();
            if(Settings==null) throw new InvalidDataException("The launcher profile is empty or invalid.");
        }
        internal string KeysText { get { return LoadedKeys ?? Native.Defaults(); } }
        internal static void AtomicWrite(string path,string text)
        {
            if(File.Exists(path) && File.ReadAllText(path,Encoding.UTF8)==text) return;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary=path+".tmp-"+Guid.NewGuid().ToString("N");
            try {
                File.WriteAllText(temporary,text,new UTF8Encoding(false));
                if(File.Exists(path)) File.Replace(temporary,path,path+".launcher-backup-"+DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff")+"-"+Guid.NewGuid().ToString("N"));
                else File.Move(temporary,path);
            } finally { if(File.Exists(temporary)) File.Delete(temporary); }
        }
        internal void Save(string keys,string iso,bool fullscreen)
        {
            string current=File.Exists(KeysPath)?File.ReadAllText(KeysPath,Encoding.UTF8):null;
            if(current!=LoadedKeys) throw new IOException("Controls changed outside this launcher. Reload settings before saving.");
            string problems=Native.Validate(keys);
            if(problems.Length>0) throw new InvalidDataException(problems);
            AtomicWrite(KeysPath,keys); LoadedKeys=keys;
            Settings.IsoPath=iso; Settings.Fullscreen=fullscreen;
            AtomicWrite(PreferencesPath,new JavaScriptSerializer().Serialize(Settings)+"\n");
        }
    }

    internal static class Runtime
    {
        internal const long IsoSize=2598567936L;
        internal const string IsoSha256="86f59b3e30012f8b4650c1dc891af9e3aec1663df49120b7eb00c5ebc2672faf";
        internal static readonly string Root=AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        internal static readonly string Framework=Path.Combine(Root,"third_party","ps2-native-recomp");
        internal static readonly string Executable=Path.Combine(Framework,"build","native-dothack-infection","ps2run.exe");
        internal static string Compiler()
        {
            var serializer=new JavaScriptSerializer();
            var data=serializer.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(Root,"dependencies.lock.json")));
            var compiler=(Dictionary<string,object>)data["compiler"];
            return Path.Combine(Root,"toolchains",(string)compiler["version"],"bin","clang++.exe");
        }
        internal static void CheckRuntime()
        {
            foreach(string file in new[]{Executable,Compiler(),Path.Combine(Framework,"build","tools","eerecomp.exe")})
                if(!File.Exists(file)) throw new FileNotFoundException("The local game build is incomplete. Follow the README build instructions first.",file);
        }
        internal static string VerifyIso(string path,Action<int> progress,Func<bool> cancel)
        {
            if(!File.Exists(path)) throw new FileNotFoundException("Select your .hack//INFECTION (USA) ISO.",path);
            var info=new FileInfo(path);
            if(!String.Equals(info.Extension,".iso",StringComparison.OrdinalIgnoreCase) || info.Length!=IsoSize)
                throw new InvalidDataException("This build requires the supported .hack//INFECTION (USA), SLUS-20267 ISO.");
            using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read,4*1024*1024,FileOptions.SequentialScan))
            using(var hash=SHA256.Create()) {
                byte[] buffer=new byte[4*1024*1024]; long read=0; int count,last=-1;
                while((count=stream.Read(buffer,0,buffer.Length))>0) {
                    if(cancel()) throw new OperationCanceledException();
                    hash.TransformBlock(buffer,0,count,buffer,0); read+=count;
                    int percent=(int)(read*100/IsoSize);
                    if(percent!=last){progress(percent);last=percent;}
                }
                hash.TransformFinalBlock(new byte[0],0,0);
                string result=BitConverter.ToString(hash.Hash).Replace("-","").ToLowerInvariant();
                if(result!=IsoSha256) throw new InvalidDataException("The ISO does not match the supported USA SLUS-20267 revision. Your file was not changed.");
                return result;
            }
        }
        internal static string Quote(string argument)
        {
            var value=new StringBuilder("\""); int slashes=0;
            foreach(char c in argument) {
                if(c=='\\') {++slashes;continue;}
                if(c=='\"') value.Append('\\',slashes*2+1).Append(c);
                else value.Append('\\',slashes).Append(c);
                slashes=0;
            }
            return value.Append('\\',slashes*2).Append('"').ToString();
        }
        internal static void ImportCompletedCaches()
        {
            var sources=new List<string>{Path.Combine(Root,"saves"),Path.Combine(Framework,"games","dothack-infection")};
            string evidence=Path.Combine(Root,"evidence");
            if(Directory.Exists(evidence)) sources.AddRange(Directory.GetDirectories(evidence,"qa-*"));
            foreach(string kind in new[]{"ee-live","vu1-live"}) {
                string destination=Path.Combine(Root,"cache",kind); Directory.CreateDirectory(destination);
                if((File.GetAttributes(destination)&FileAttributes.ReparsePoint)!=0) throw new IOException("The code cache must be inside the project.");
                foreach(string source in sources) {
                    string folder=Path.Combine(source,kind);
                    if(!Directory.Exists(folder)||(File.GetAttributes(folder)&FileAttributes.ReparsePoint)!=0) continue;
                    string[] libraries=Directory.GetFiles(folder,"*.dll");
                    var files=new List<string>(libraries);
                    if(kind=="ee-live" && libraries.Length>0) files.AddRange(Directory.GetFiles(folder,"*.mark"));
                    foreach(string file in files) {
                        if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0) continue;
                        string target=Path.Combine(destination,Path.GetFileName(file));
                        if(!File.Exists(target)) File.Copy(file,target);
                        else if(Path.GetExtension(file)==".mark" && File.ReadAllText(target).StartsWith("fast") && !File.ReadAllText(file).StartsWith("fast")) File.Copy(file,target,true);
                    }
                }
            }
        }
        internal static ProcessStartInfo StartInfo(string iso,Profile profile,bool fullscreen,int qaFrames)
        {
            CheckRuntime();
            string args="--disc "+Quote(iso)+" --window --game-dir "+Quote(profile.DirectoryPath)+" --memcard "+Quote(Path.Combine(profile.DirectoryPath,"card1.ps2"));
            if(fullscreen) args+=" --fullscreen";
            if(qaFrames>0) args+=" --frames "+qaFrames;
            var info=new ProcessStartInfo(Executable,args) {WorkingDirectory=Framework,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
            string compiler=Compiler();
            info.EnvironmentVariables["PATH"]=Path.GetDirectoryName(compiler)+Path.PathSeparator+info.EnvironmentVariables["PATH"];
            info.EnvironmentVariables["PS2_EE_LIVE"]=Path.Combine(Root,"cache","ee-live");
            info.EnvironmentVariables["PS2_VU_LIVE"]=Path.Combine(Root,"cache","vu1-live");
            info.EnvironmentVariables["PS2_VU_CXX"]=compiler;
            info.EnvironmentVariables["PS2_EE_LIVE_JOBS"]="2";
            info.EnvironmentVariables["PS2_PAD_STICK_CENTER"]="127";
            info.EnvironmentVariables["PS2_VU_KICK_DELAY"]="2";
            info.EnvironmentVariables["PS2_VU_INTERPRET_KEYS"]="075E2EE535A64DB5";
            info.EnvironmentVariables["PS2_WINDOW_TITLE"]=".hack//INFECTION Recompiled (Experimental)";
            info.EnvironmentVariables["PS2_KEYS"]=profile.KeysPath;
            foreach(string key in new[]{"PS2_SCALE","PS2_LOOK","PS2_SHARP_2D"}) info.EnvironmentVariables.Remove(key);
            return info;
        }
    }
}
