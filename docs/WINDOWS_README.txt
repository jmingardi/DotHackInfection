.hack//INFECTION - experimental Windows x64 build

Extract the entire ZIP into a writable folder and run DotHackInfection.exe.
Select your own supported USA SLUS-20267 ISO in the launcher, wait for the
image verification to finish, then press Play. No Python, command prompt or
separately installed build tools are needed for ordinary use. Keep all ZIP
contents together: a private copy of the compiler is bundled because additional
game code is compiled during play. First encounters can pause for compilation.

Requires Windows x64, .NET Framework 4.8, an AVX2-capable CPU and compatible
graphics drivers. Tested gameplay covers the opening through the first dungeon;
full campaign compatibility is not established. The portable build uses the
Windows shader compiler (FXC); Microsoft DXC binaries are not redistributed.

Game: ISO selection/verification, Play, saves and last startup log.
Display: windowed/borderless, internal resolution, picture/text filters.
Controls: keyboard/mouse capture and standard SDL2 controller detection.
F1 opens the runtime settings during play. Saves and preferences are stored in
saves/ beside the launcher; generated code caches are stored in cache/.

No disc image, extracted retail executable, BIOS, personal save, or prefilled
gameplay cache is included. This is an unofficial project. Game names and other
game intellectual property belong to their respective owners.

Source and build documentation: https://github.com/jmingardi/DotHackInfection
Included third-party notices are under licenses/, launcher-bin/licenses/ and
toolchains/. Keep these notices with the files when sharing this package.
