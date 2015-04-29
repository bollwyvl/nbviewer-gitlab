# Jupyter Notebook Viewer GitLab Provider
This is an experimental implementation of an
[nbviewer](/jupyter/nbviewer) provider. When it works, it should render public 
notebooks on an arbitrary GitLab instance.

> The upstream work to support this is ongoing. For the current state of that 
effort, see the [pull request](/jupyter/nbviewer/pull/443) and
original [issue](/jupyter/nbviewer/issues/428).

> This could some day become an implementation for the
[feature request](/jupyter/nbviewer/issues/371)!


## Developing
Install [docker](https://docs.docker.com/installation/) and 
[docker-compose](http://docs.docker.com/compose/install/).

```
docker-compose up
```

When it is finished, you should have:
- a GitLab instance running on [10080](http://localhost:10080)
- an nbviewer instance running on [8080](http://localhost:8080)

## Roadmap
- [ ] Inject some sample notebooks?
  - [ ] maybe this repo?
  - [ ] baked-in, or scripts after the fact?
- [ ] Implement user proxy?
- [ ] Deployment post?