PORTNAME=	renasync-gui
DISTVERSION=	0.0.1
CATEGORIES=	multimedia

MAINTAINER=	Konpaku-LVX@users.noreply.github.com
COMMENT=	Lightweight GUI addon for Renasync
WWW=		https://github.com/Konpaku-LVX/renasync-gui

LICENSE=	BSD0CLAUSE

LIB_DEPENDS=	libmpv.so:multimedia/mpv
BUILD_DEPENDS=	${PYTHON_PKGNAMEPREFIX}setuptools>=0:devel/py-setuptools@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}wheel>=0:devel/py-wheel@${PY_FLAVOR}
RUN_DEPENDS=	renasync>=0:multimedia/renasync \
		${PYTHON_PKGNAMEPREFIX}tkinter>=0:x11-toolkits/py-tkinter@${PY_FLAVOR}

USES=		python:3.10+
USE_PYTHON=	autoplist pep517

USE_GITHUB=	yes
GH_ACCOUNT=	Konpaku-LVX
GH_PROJECT=	renasync-gui
GH_TAGNAME=	v0.0.1

post-patch:
	${REINPLACE_CMD} -e '/^license-files/d' ${WRKSRC}/pyproject.toml

.include <bsd.port.mk>
