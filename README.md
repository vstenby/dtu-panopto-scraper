# dtu-panopto-scraper

Download videos, descriptions and subtitles from [panopto.dtu.dk](https://panopto.dtu.dk/). Note that this requires a DTU login to [panopto.dtu.dk](https://panopto.dtu.dk) and can therefore only be used by students at the Technical University of Denmark. 

## Installation

Clone the repository and install the required packages using the `requirements.txt` file.

```
python -m pip install -r requirements.txt
```

## Folder Structure

After cloning the project, the folder structure should look like this:

```
.
├── LICENSE
├── README.md
├── export
├── ffmpeg_utils.py
├── main.py
├── requirements.txt
└── scrape_utils.py
```

and after having downloaded a video, the `export` folder will be populated with a subfolder containing your video, subtitles and metadata (depending on your arguments):

```
.
├── LICENSE
├── README.md
├── export
│   └── 2503d1d6-5702-4bab-981b-af27011a7cf1
│       ├── komplekse-tal-del1.json
│       ├── komplekse-tal-del1.m3u8
│       ├── komplekse-tal-del1.mp4
│       └── komplekse-tal-del1.txt
├── ffmpeg_utils.py
├── main.py
├── requirements.txt
└── scrape_utils.py
```

## Usage 

To see all of the arguments to `main.py`, you can write ``python main.py --help``.

Below are a few examples!

### Downloading a single video

If you want to download a single Panopto video, e.g. [this one](https://panopto.dtu.dk/Panopto/Pages/Viewer.aspx?id=2503d1d6-5702-4bab-981b-af27011a7cf1&query=komplekse%20tal%20del%201), then you can do that by calling:

```
python main.py --url "https://panopto.dtu.dk/Panopto/Pages/Viewer.aspx?id=2503d1d6-5702-4bab-981b-af27011a7cf1&query=komplekse%20tal%20del%201"
```

### Downloading a folder of videos

If you want to download a folder of videos, e.g. [this one](https://panopto.dtu.dk/Panopto/Pages/Sessions/List.aspx#folderID=%22a488e829-1543-4366-ba0f-af24007c188c%22). 

```
python main.py --url "https://panopto.dtu.dk/Panopto/Pages/Sessions/List.aspx#folderID=%22a488e829-1543-4366-ba0f-af24007c188c%22"
```

### Only subtitles and metadata

If you are only interested in downloading the subtitles and metadata, you can add the `--no-lecture` flag. 
