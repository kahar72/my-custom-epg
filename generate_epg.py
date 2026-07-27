import gzip
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

CHANNELS_FILE = "ChannelsID.txt"
SOURCES_FILE = "EPGSources.txt"

def load_target_ids():
    """Load and clean channel IDs from ChannelsID.txt."""
    target_ids = set()
    if not os.path.exists(CHANNELS_FILE):
        print(f"Warning: {CHANNELS_FILE} not found.")
        return target_ids

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Clean up tvg-id="xxx" or quotes if present
                cleaned_id = re.sub(r'^tvg-id=["\']?|["\']$', '', line).strip()
                if cleaned_id:
                    target_ids.add(cleaned_id)
                
    print(f"Loaded {len(target_ids)} target channel IDs from {CHANNELS_FILE}.")
    return target_ids

def load_epg_sources():
    """Load EPG source URLs and optional prefixes from EPGSources.txt."""
    sources = []
    if not os.path.exists(SOURCES_FILE):
        print(f"Warning: {SOURCES_FILE} not found.")
        return sources

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(",")
                url = parts[0].strip()
                prefix = parts[1].strip() if len(parts) > 1 else ""
                sources.append({"url": url, "prefix": prefix})

    print(f"Loaded {len(sources)} EPG sources from {SOURCES_FILE}.")
    return sources

def fetch_and_parse(url):
    """Download and parse XML or XML.GZ."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        if url.endswith('.gz'):
            data = gzip.decompress(data)
        return ET.fromstring(data)

def main():
    target_ids = load_target_ids()
    epg_sources = load_epg_sources()

    out_root = ET.Element('tv')
    processed_channels = set()

    for source in epg_sources:
        url = source["url"]
        prefix = source["prefix"]
        print(f"Processing: {url} (Prefix: '{prefix}')")

        try:
            tree_root = fetch_and_parse(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        # Process Channels
        for channel in tree_root.findall('channel'):
            orig_id = channel.get('id')
            new_id = f"{prefix}{orig_id}" if prefix else orig_id

            # Keep channel if matched
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
