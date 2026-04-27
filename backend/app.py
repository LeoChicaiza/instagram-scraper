from flask import Flask, jsonify, request
from flask_cors import CORS
import instaloader
import json
import os
import time
import random

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def scrape_profile(username: str, max_posts: int = 10, session_file: str = None):
    """
    Scrapes public Instagram profile using Instaloader.
    Optionally loads a saved session for better access.
    """
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Load session if provided (cookies)
    if session_file and os.path.exists(session_file):
        try:
            L.load_session_from_file(session_file)
        except Exception as e:
            print(f"[WARN] Could not load session: {e}")

    try:
        profile = instaloader.Profile.from_username(L.context, username)

        profile_data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "biography": profile.biography,
            "followers": profile.followers,
            "followees": profile.followees,
            "posts_count": profile.mediacount,
            "is_private": profile.is_private,
            "is_verified": profile.is_verified,
            "profile_pic_url": profile.profile_pic_url,
            "external_url": profile.external_url or "",
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        posts = []
        for i, post in enumerate(profile.get_posts()):
            if i >= max_posts:
                break

            post_data = {
                "shortcode": post.shortcode,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "date": post.date_utc.isoformat(),
                "likes": post.likes,
                "comments": post.comments,
                "caption": post.caption[:300] if post.caption else "",
                "media_type": "Video" if post.is_video else "Image",
                "thumbnail_url": post.url,
                "location": post.location.name if post.location else None,
                "hashtags": list(post.caption_hashtags) if post.caption_hashtags else [],
                "mentions": list(post.caption_mentions) if post.caption_mentions else [],
            }
            posts.append(post_data)

            # Respectful delay to avoid rate limiting
            time.sleep(random.uniform(1.5, 3.0))

        profile_data["posts"] = posts

        # Save to JSON file
        output_file = os.path.join(DATA_DIR, f"{username}_profile.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2, default=str)

        return {"success": True, "data": profile_data, "file": output_file}

    except instaloader.exceptions.ProfileNotExistsException:
        return {"success": False, "error": f"Profile '{username}' does not exist."}
    except instaloader.exceptions.PrivateProfileNotFollowedException:
        return {"success": False, "error": f"Profile '{username}' is private."}
    except instaloader.exceptions.ConnectionException as e:
        return {"success": False, "error": f"Connection error (rate limited?): {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/api/scrape", methods=["POST"])
def scrape():
    body = request.get_json()
    username = body.get("username", "").strip().lstrip("@")
    max_posts = min(int(body.get("max_posts", 10)), 50)  # cap at 50

    if not username:
        return jsonify({"success": False, "error": "Username is required"}), 400

    result = scrape_profile(username, max_posts)
    return jsonify(result)


@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    """Returns list of already-scraped profiles from disk."""
    profiles = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith("_profile.json"):
            path = os.path.join(DATA_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    profiles.append({
                        "username": data.get("username"),
                        "full_name": data.get("full_name"),
                        "followers": data.get("followers"),
                        "posts_count": data.get("posts_count"),
                        "scraped_at": data.get("scraped_at"),
                        "posts_scraped": len(data.get("posts", [])),
                    })
                except Exception:
                    pass
    return jsonify(profiles)


@app.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    """Returns full profile data from disk."""
    path = os.path.join(DATA_DIR, f"{username}_profile.json")
    if not os.path.exists(path):
        return jsonify({"error": "Profile not found. Scrape it first."}), 404
    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


if __name__ == "__main__":
    print("🚀 Instagram Scraper API running at http://localhost:5000")
    app.run(debug=True, port=5000)
