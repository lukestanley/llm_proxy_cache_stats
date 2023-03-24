
# LLM Proxy Cache Stats :bar_chart: :robot: :floppy_disk: :zap:

  

Ahoy, mateys! LLM Proxy Cache Stats be a Python application that caches requests to the OpenAI API and provides basic analytics on the requests and responses. Inspired by the legendary Helicone, this here treasure be simpler and easier to set up. Arrr! No need for a database, nor Cloudflare.

  

## :rocket: Quick Start :anchor:

  

To run the cache, ye need to have Python 3.

Clone this repository and install the dependencies using pip, me hearties:

  

```bash

git clone  https://github.com/lukestanley/llm_proxy_cache_stats.git

cd  llm_proxy_cache_stats

pip install  -r  requirements.txt

python cache_openai.py

```

  

## The cache be savin' to disk up to every 10 seconds. :hourglass:

  

To run the stats server, use the followin' command, ye scallywags:

  

```bash

streamlit run  cache_stats.py

```

  

The statistics be populated on load, aye.

  

## To use the cache, set the API base to the cache server: :compass:

```python

import openai

openai.api_base = "http://localhost:5000/v1"

```

  

## :gear: Configuration :scroll:

  

Ye can customise the behaviour of the cache by modifyin' the `cache_openai.py` file, me hearties. Tweak it to your likin' and sail the high seas of AI analytics with ease! :pirate_flag: :parrot:
