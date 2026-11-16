using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;

namespace DotHackInfection
{
    internal static class SelfTest
    {
        [DllImport("shell32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CommandLineToArgvW(string command,out int count);
        [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
        static readonly List<string> passed=new List<string>();
        static void Check(bool condition,string name) {if(!condition)throw new Exception("Self-test failed: "+name);passed.Add(name);}
        static void Reject(Action action,string name){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,name);}
        internal static void Run(string directory)
        {
            if(Directory.Exists(directory)&&Directory.GetFileSystemEntries(directory).Length>0)throw new IOException("Self-test needs a fresh isolated profile.");
            Directory.CreateDirectory(directory);
            string keys=Native.Defaults()+"\n# Preserve custom comment: a\u00e7\u00e3o\npace = 30\n";
            Check(Native.Validate(keys)=="","native default bindings parse");
            string changed=Native.Bind(keys,12,Native.SDL_GetScancodeFromName(Native.Utf8("W")));
            var values=Native.Values(changed);
            Check(values["12"]=="W","keyboard capture changes Cross");
            Check(values["4"].Contains("Space"),"duplicate input uses upstream swap semantics");
            Reject(()=>Native.Bind(keys,12,Native.SDL_GetScancodeFromName(Native.Utf8("F1"))),"reserved F1 is rejected");
            Reject(()=>Native.SetBinding(keys,12,"not a real key"),"unknown binding is rejected");
            changed=Native.SetBinding(keys,12,"G, Enter");
            Check(Native.Values(changed)["12"].Contains("G")&&Native.Values(changed)["12"].Contains("Enter"),"multiple key alternatives round trip");
            changed=Native.Bind(keys,15,1002);
            Check(Native.Values(changed)["15"]=="Right Mouse","mouse binding round trip");
            changed=Native.Options(changed,0,2,2);
            values=Native.Values(changed);
            Check(values["look"]=="0"&&values["scale"]=="2"&&values["sharp"]=="2","display preferences use runtime keymap");
            Check(changed.Contains("# Preserve custom comment: a\u00e7\u00e3o")&&changed.Contains("pace = 30"),"unrelated comments and pacing preserved");
            Check(Native.Values(Native.Reset(Native.SetBinding(changed,12,"G")))["12"].Contains("Space"),"restore default game bindings");
            string card=Path.Combine(directory,"card1.ps2");byte[] original={1,2,3,4,5,6};File.WriteAllBytes(card,original);
            string path=Path.Combine(directory,"keys.ini");File.WriteAllText(path,keys,new UTF8Encoding(false));
            var profile=new Profile(directory);
            profile.Save(changed,Path.Combine(Runtime.Root,"Dot Hack Part 1 - Infection (USA).iso"),true);
            Check(BitConverter.ToString(File.ReadAllBytes(card))==BitConverter.ToString(original),"saving launcher preferences preserves memory card");
            Check(Directory.GetFiles(directory,"keys.ini.launcher-backup-*").Length==1,"existing bindings backed up before atomic replacement");
            profile.Reload();
            Check(profile.Settings.Fullscreen&&profile.Settings.IsoPath.EndsWith(".iso"),"ISO and fullscreen preferences survive restart");
            Check(profile.LoadedKeys==changed,"controls and display survive restart");
            File.AppendAllText(path,"# external edit\n");
            Reject(()=>profile.Save(changed,"",false),"external settings edits are not overwritten");
            var info=Runtime.StartInfo(profile.Settings.IsoPath,profile,true,120);
            Check(info.FileName==Runtime.Executable&&!info.FileName.EndsWith("python.exe"),"Play starts native EXE without Python or CMD");
            Check(info.EnvironmentVariables["PS2_PAD_STICK_CENTER"]=="127"&&info.EnvironmentVariables["PS2_VU_KICK_DELAY"]=="2"&&info.EnvironmentVariables["PS2_VU_INTERPRET_KEYS"]=="075E2EE535A64DB5","title compatibility profile preserved");
            Check(info.EnvironmentVariables["PS2_KEYS"]==profile.KeysPath&&info.Arguments.Contains("--memcard")&&info.Arguments.Contains("--fullscreen"),"native runtime receives profile and display options");
            Check(info.EnvironmentVariables["PS2_SCALE"]==null&&info.EnvironmentVariables["PS2_LOOK"]==null,"launcher settings remain editable in F1 menu");
            foreach(string value in new[]{@"C:\game path\disc.iso",@"C:\trailing\","a\"quoted\\path", "a\u00e7\u00e3o.iso"}) {
                int count;IntPtr argv=CommandLineToArgvW("game.exe "+Runtime.Quote(value),out count);
                try{Check(count==2&&Marshal.PtrToStringUni(Marshal.ReadIntPtr(argv,IntPtr.Size))==value,"Windows argument round trip: "+value);}finally{LocalFree(argv);}
            }
            Reject(()=>Runtime.VerifyIso(Path.Combine(directory,"missing.iso"),p=>{},()=>false),"missing ISO rejected");
            string invalid=Path.Combine(directory,"wrong.iso");File.WriteAllText(invalid,"wrong disc");
            Reject(()=>Runtime.VerifyIso(invalid,p=>{},()=>false),"unsupported ISO rejected before launch");
            Check(File.ReadAllText(invalid)=="wrong disc","disc verification never writes the ISO");
            File.WriteAllText(Path.Combine(directory,"self-test.json"),new JavaScriptSerializer().Serialize(new {passed=passed.Count,checks=passed})+"\n",Encoding.UTF8);
        }
    }
}
