import gzip
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

# Fetch playlist from secret
PLAYLIST_URL = os.environ.get("PLAYLIST_URL")

# EPG Sources — Only UnifiTV gets the "unifitv." prefix
EPG_SOURCES = [
    {"url": "https://raw.githubusercontent.com/dbghelp/StarHub-TV-EPG/refs/heads/main/starhub.xml", "prefix": ""},
    {"url": "https://raw.githubusercontent.com/AqFad2811/epg/refs/heads/main/unifitv.xml", "prefix": "unifitv."},
    {"url": "https://raw.githubusercontent.com/AqFad2811/epg/refs/heads/main/epg.xml", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_NZ1.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_AU1.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_CA2.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS1.xml.gz", "prefix": ""},
    {"url": "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz", "prefix": ""},
]

def get_playlist_ids():
    """Extract tvg-id values from the M3U playlist."""
    ids = set()
    if not PLAYLIST_URL:
        print("Warning: PLAYLIST_URL secret not found.")
        return ids
    
    req = urllib.request.Request(PLAYLIST_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'tvg-id="([^"]+)"', content)
        ids.update(matches)
    print(f"Loaded {len(ids)} target tvg-ids from playlist.")
    return ids

def fetch_and_parse(url):
    """Download and parse XML or XML.GZ."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        if url.endswith('.gz'):
            data = gzip.decompress(data)
        return ET.fromstring(data)

def main():
    target_ids = get_playlist_ids()
    out_root = ET.Element('tv')
    processed_channels = set()

    for source in EPG_SOURCES:
        url = source["url"]
        prefix = source["prefix"]
        print(f"Processing: {url}")
        
        try:
            tree_root = fetch_and_parse(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        # Process Channels
        for channel in tree_root.findall('channel'):
            orig_id = channel.get('id')
            new_id = f"{prefix}{orig_id}" if prefix else orig_id
            
            # Keep channel if in playlist (or keep all if playlist secret is empty)
            if not target_ids or new_id in target_ids or orig_id in target_ids:
                if new_id not in processed_channels:
                    channel.set('id', new_id)
                    out_root.append(channel)
                    processed_channels.add(new_id)

        # Process Programs
        for programme in tree_root.findall('programme'):
            orig_channel = programme.get('channel')
            new_channel = f"{prefix}{orig_channel}" if prefix else orig_channel
            
            if new_channel in processed_channels:
                programme.set('channel', new_channel)
                out_root.append(programme)

    # Export compressed XMLTV file
    output_xml = ET.tostring(out_root, encoding='utf-8', xml_declaration=True)
    with gzip.open('epg.xml.gz', 'wb') as f:
        f.write(output_xml)
    print("EPG generation complete: epg.xml.gz created.")

if __name__ == "__main__":
    main()
