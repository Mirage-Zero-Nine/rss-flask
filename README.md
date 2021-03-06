# rss-flask

## What is this?

This is a simple web service written in Python to generate RSS feed for websites. Currently only few websites are supported (see `app.py` for details). I'm trying to add more routers to the service.

## Deployment

- Create a directory: `mkdir YOUR_DIRECTORY_NAME`.
- Move to the directory and clone this repo: `cd YOUR_DIRECTORY_NAME && git clone https://github.com/Mirage-Zero-Nine/rss-flask.git`.
- Create a `authentication.yaml` (required only if you want to generate Twitter user feed) to store your Twitter BEARER_TOKEN:
  Sample:
  ```yaml
  token:
    twitter_token: YOUR_TOKEN_HERE
  ```
- Build docker image: `docker build -t YOUR_IMAGE_NAME .`
- Start container: `docker run -d --restart=always --name=YOUR_CONTAINER_NAME -p 5000:5000 YOUR_IMAGE_NAME:latest`.
- Now you can access the RSS file via `localhost:5000/PATH_TO_ROUTER` to access RSS router.

## Dependency

See `requirement.txt`. It is generated by `pip3 freeze > requirements.txt`

## Routers

See `app.py` for router path. 

### Parameters for router
- `/currency/<currency_name>`: only support CNY to USD, `currency_name` is a placeholder for future usage.
- `/twitter/<user_name>`: replace `user_name` with the Twitter username you want to subscribe. Support `excludeRetweet` and  `excludeReply` as query parameter. Sample usage: `/twitter/SOME_USER_NAME?excludeReply=true&excludeRetweet=true`.
- `/zaobao/realtime/<region>`: two regions supported for now: `world` and `china`.

## Known Issue
- No demo provided for this service. You will need to deploy the service on your own computer, or a cloud host (e.g.: Amazon EC2).
- RSS feed time may not be incorrect since I'm still trying to figure out how to correctly set timezone info in `datetime` object. The cloud host I used to deploy this service use UTC and you may need to align with that to avoid timezone issue.  

## One more thing

Actually most of the news websites are providing their own RSS feed for users to subscribe. However, not for the media in China.. That's the original reason why I want to create this tiny RSS service and you can see most of the routers are linked to the website in China.
