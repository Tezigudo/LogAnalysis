from github import Github
from decouple import config

def find_repositories_with_criteria(language, min_stars):
    # GitHub API access token or your GitHub username and password
    g = Github(config('GITHUB_ACCESS_TOKEN'))

    repositories = []

    try:
        # Searching repositories based on criteria
        query = f'language:{language} in:pom.xml stars:>{min_stars}'
        result = g.search_repositories(query=query, sort='stars', order='desc')

        # Extracting repository information
        for repo in result:
            repository = {
                'name': repo.full_name,
                'stars': repo.stargazers_count,
                'url': repo.html_url
            }
            repositories.append(repository)

    except Exception as e:
        print('Error fetching data:', e)

    return repositories

if __name__ == "__main__":
    language = "Java"
    min_stars = 30

    repositories = find_repositories_with_criteria(language, min_stars)

    print(f"Repositories with more than {min_stars} stars, written in {language}\n")
    for repo in repositories:
        print(f"{repo['name']} - {repo['stars']} stars ({repo['url']})")
