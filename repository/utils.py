def import_class(class_string):
    """
    import class from classpath string

    >>> repo_class = import_class("repository.cloudfront.CloudFront")
    >>> repo
    <class 'repository.cloudfront.cloudfront.CloudFront'>
    >>> repo = repo_class("/basepath/")
    """
    fullpath = class_string.split(".")
    from_module = ".".join(fullpath[:-1])
    classname = fullpath[-1]
    module = __import__(from_module, fromlist=[classname])
    return getattr(module, classname)
