import streamlit as st
import json
from datetime import datetime
from azure.cosmos import CosmosClient
import html


def initialize_cosmos_client():
    endpoint = st.secrets["cosmosdb"]["COSMOS_DB_ENDPOINT"]
    key = st.secrets["cosmosdb"]["COSMOS_DB_KEY"]
    client = CosmosClient(endpoint, key)
    database = client.get_database_client(
        st.secrets["cosmosdb"]["COSMOS_DB_DATABASE_NAME"])
    container = database.get_container_client(
        st.secrets["cosmosdb"]["COSMOS_DB_CONTAINER_NAME"])
    return container


def get_last_10_tweets(container):
    query = """
    SELECT TOP 10 *
    FROM c
    ORDER BY c.created_at DESC
    """
    return list(container.query_items(query=query, enable_cross_partition_query=True))


def get_elon_tweets(container, limit=10):
    query = f"""
    SELECT TOP {limit} *
    FROM c
    WHERE c.author.username = 'elonmusk'
    ORDER BY c.created_at DESC
    """
    return list(container.query_items(query=query, enable_cross_partition_query=True))


def get_tweet_thread(container, tweet):
    thread = [tweet]
    current_tweet = tweet
    while 'referenced_tweets' in current_tweet:
        for ref in current_tweet['referenced_tweets']:
            if ref['type'] == 'replied_to':
                query = f"SELECT * FROM c WHERE c.id = '{ref['id']}'"
                items = list(container.query_items(
                    query=query, enable_cross_partition_query=True))
                if items:
                    thread.insert(0, items[0])
                    current_tweet = items[0]
                    break
        else:
            break
    return thread


def format_date(date_string):
    tweet_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    return tweet_date.strftime("%I:%M %p · %b %d, %Y")


def display_tweet_thread(thread):
    st.markdown("""
    <style>
    .tweet-container {
        border: 1px solid #cfd9de;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: #ffffff;
    }
    .referenced-tweet {
        background-color: #f7f9f9;
    }
    .reply-tweet {
        margin-left: 20px;
        border-left: 2px solid #cfd9de;
    }
    .replying-to {
        color: #536471;
        font-size: 13px;
        margin-left: 20px;
        margin-bottom: 5px;
    }
    .tweet-header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .tweet-author-image {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .tweet-author-name {
        font-weight: bold;
        margin-bottom: 0;
    }
    .tweet-author-username {
        color: #536471;
    }
    .tweet-text {
        margin-bottom: 12px;
    }
    .tweet-date {
        color: #536471;
        font-size: 14px;
        margin-bottom: 12px;
    }
    .tweet-metrics {
        display: flex;
        justify-content: space-between;
        color: #536471;
    }
    </style>
    """, unsafe_allow_html=True)

    for i, tweet in enumerate(thread):
        css_class = "referenced-tweet" if i < len(thread) - \
            1 else "reply-tweet"
        st.markdown(
            f'<div class="tweet-container {css_class}">', unsafe_allow_html=True)
        display_tweet_content(tweet)
        st.markdown('</div>', unsafe_allow_html=True)

        if i < len(thread) - 1:
            username = tweet.get("author", {}).get("username", "Unknown")
            st.markdown(
                f'<p class="replying-to">Replying to @{html.escape(username)}</p>', unsafe_allow_html=True)


def display_tweet_content(tweet):
    # Tweet header
    profile_image_url = tweet.get('author', {}).get('profile_image_url', '')
    name = html.escape(tweet.get('author', {}).get('name', 'Unknown'))
    username = html.escape(tweet.get('author', {}).get('username', 'unknown'))

    st.markdown(f"""
    <div class="tweet-header">
        <img src="{profile_image_url}" class="tweet-author-image">
        <div>
            <p class="tweet-author-name">{name}</p>
            <p class="tweet-author-username">@{username}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tweet text
    text = html.escape(tweet.get("text", ""))
    st.markdown(f'<p class="tweet-text">{text}</p>', unsafe_allow_html=True)

    # Media
    if 'media' in tweet:
        for media in tweet['media']:
            if media['type'] == 'photo':
                st.image(media.get('url', ''))
            elif media['type'] == 'video':
                st.write("Video content available (cannot be displayed directly)")
                if 'preview_image_url' in media:
                    st.image(media['preview_image_url'])

    # Tweet date
    created_at = tweet.get("created_at", "")
    if created_at:
        st.markdown(
            f'<p class="tweet-date">{format_date(created_at)}</p>', unsafe_allow_html=True)

    # Tweet metrics
    public_metrics = tweet.get("public_metrics", {})
    metrics_html = '<div class="tweet-metrics">'
    metrics_html += f'<span>🔁 {public_metrics.get("retweet_count", 0)}</span>'
    metrics_html += f'<span>💬 {public_metrics.get("reply_count", 0)}</span>'
    metrics_html += f'<span>❤️ {public_metrics.get("like_count", 0)}</span>'
    metrics_html += f'<span>🔄 {public_metrics.get("quote_count", 0)}</span>'
    metrics_html += f'<span>🔖 {
        public_metrics.get("bookmark_count", "N/A")}</span>'
    metrics_html += f'<span>👁️ {public_metrics.get(
        "impression_count", "N/A")}</span>'
    metrics_html += '</div>'
    st.markdown(metrics_html, unsafe_allow_html=True)

    # Additional Tweet Information
    with st.expander("Additional Tweet Information"):
        st.json({
            "id": tweet.get('id', ''),
            "conversation_id": tweet.get('conversation_id', ''),
            "lang": tweet.get('lang', ''),
            "possibly_sensitive": tweet.get('possibly_sensitive', 'N/A'),
            "reply_settings": tweet.get('reply_settings', 'N/A'),
            "edit_controls": tweet.get('edit_controls', 'N/A'),
            "author_info": {
                "id": tweet.get('author', {}).get('id', ''),
                "created_at": tweet.get('author', {}).get('created_at', ''),
                "description": tweet.get('author', {}).get('description', 'N/A'),
                "location": tweet.get('author', {}).get('location', 'Not specified'),
                "verified": tweet.get('author', {}).get('verified', 'N/A'),
                "verified_type": tweet.get('author', {}).get('verified_type', 'Not specified'),
                "public_metrics": tweet.get('author', {}).get('public_metrics', {})
            }
        })


def main():
    st.set_page_config(layout="wide")

    container = initialize_cosmos_client()

    # Sidebar
    st.sidebar.title("Options")
    display_option = st.sidebar.radio(
        "Choose what to display:",
        ("Last 10 Elon Tweets", "All Tweet Threads")
    )

    if display_option == "Last 10 Elon Tweets":
        st.title("Elon Musk's Last 10 Tweets")
        tweets = get_elon_tweets(container)

        for i, tweet in enumerate(tweets, 1):
            st.subheader(f"Tweet {i}")
            thread = get_tweet_thread(container, tweet)
            display_tweet_thread(thread)
            st.markdown("---")
    else:
        st.title("All Tweet Threads")
        tweets = get_last_10_tweets(container)

        for i, tweet in enumerate(tweets, 1):
            st.subheader(f"Tweet Thread {i}")
            thread = get_tweet_thread(container, tweet)
            display_tweet_thread(thread)
            st.markdown("---")


if __name__ == "__main__":
    main()
