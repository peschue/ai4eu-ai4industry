IP=$(ifconfig eth0 |grep "inet "|cut -d" " -f10)
pipenv run jupyter notebook --ip=$IP --no-browser
