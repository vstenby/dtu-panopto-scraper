import subprocess
import os


def download(m3u8_path: str, out_format: str = ".mp3") -> None:
    """
    Downloads the video. If the panopto video contains multiple videos, then this function will download all of them.
    The videos will be saved to the same folder as the m3u8 files are located.

    Args:
        m3u8_paths, list containing the paths to the m3u8 files.
        file_type_out, the file type to save the video as. Default is .mp4.
    Returns:
        None
    """

    outpath = m3u8_path.replace(".m3u8", out_format)

    if outpath.endswith(".mp4"):
        bashcmd = f"ffmpeg -y -protocol_whitelist file,http,https,tcp,tls,crypto -i {m3u8_path} -c copy -bsf:a aac_adtstoasc {os.path.basename(outpath)}"
    elif outpath.endswith(".mp3"):
        bashcmd = f"ffmpeg -y -protocol_whitelist file,http,https,tcp,tls,crypto -i {m3u8_path} -q:a 2 {os.path.basename(outpath)}"
    else:
        raise ValueError("The file type must be either .mp4 or .mp3")

    subprocess.run(
        bashcmd,
        shell=True,
        capture_output=True,
    )

    os.rename(src=os.path.basename(outpath), dst=outpath)
    return
