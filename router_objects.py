from router.meta_blog.meta_blog import MetaBlog
from router.meta_blog.meta_router_constants import meta_blog_router_name, meta_blog_title, meta_blog_rss_link, \
    meta_blog_link, meta_blog_description, meta_blog_key, meta_blog_period
from utils.router_constants import language_english

meta_blog = MetaBlog(meta_blog_router_name,
                     meta_blog_title,
                     meta_blog_rss_link,
                     meta_blog_link,
                     meta_blog_description,
                     language_english,
                     meta_blog_key,
                     meta_blog_period)
