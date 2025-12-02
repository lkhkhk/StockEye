# `docker` 설치 및 설정 가이드

```bash

sudo snap instsll docker

# snap 로 설치하면 일반사용로 설치되어 권한문제 발생하므로 다음과 같이 doker 그룹에 포함시키고, docker 를 system 그룸에 추가한다.

sudo addgroup -- system docker
sudo adduser $USER docker
newgrep docker
sudo snap disable docker
sudo snap enable docker

```