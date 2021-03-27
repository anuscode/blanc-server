"""Admin blue print definitions."""

import pendulum
import uuid

from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from firebase_admin import storage
from model.models import User, Report, Post

mimetype = "application/json"

report_blueprint = Blueprint("report_blueprint", __name__)


@report_blueprint.route("/report/reporter/<reporter_id>/reportee/<reportee_id>", methods=["POST"])
def route_create_report(reporter_id: str, reportee_id: str):
    """Creates new report."""
    uid = request.headers.get("uid", None)

    params = request.form.to_dict(flat=True)
    report_images = request.files.values()
    description = params.get("description", None)
    reported_at = pendulum.now().int_timestamp

    reporter = User.objects.get_or_404(id=reporter_id)
    reportee = User.objects.get_or_404(id=reportee_id)

    if reporter.uid != uid:
        abort(401)

    report_image_urls = []
    for report_image in report_images:
        # update to image server
        bucket = storage.bucket()
        reporter_nickname = reporter.nickname
        reportee_nickname = reportee.nickname
        report_url_format = 'report_images/{uid}/{timestamp}_{uuid}.jpeg'
        blob = bucket.blob(report_url_format.format(
            uid=uid,
            reporter_nickname=reporter_nickname,
            reportee_nickname=reportee_nickname,
            timestamp=pendulum.now().int_timestamp,
            uuid=uuid.uuid1())
        )
        blob.upload_from_file(report_image)
        report_image_urls.append(blob.public_url)

    report = Report(
        reporter=reporter,
        reportee=reportee,
        description=description,
        reported_at=reported_at,
        report_images=report_image_urls,
        is_resolved=False
    )
    report.save()

    return Response("", mimetype=mimetype)


@report_blueprint.route("/report/reporter/<reporter_id>/posts/<post_id>", methods=["POST"])
def route_create_post_report(reporter_id: str, post_id: str):
    """Creates new report."""
    params = request.form.to_dict(flat=True)
    report_images = request.files.values()
    description = params.get("description", None)
    reported_at = pendulum.now().int_timestamp

    reporter = User.objects.get_or_404(id=reporter_id)
    reporter.identify(request)
    uid = reporter.uid
    post = Post.objects.get_or_404(id=post_id)
    reportee = post.author

    report_image_urls = []
    for report_image in report_images:
        # update to image server
        bucket = storage.bucket()
        reporter_nickname = reporter.nickname
        reportee_nickname = reportee.nickname
        report_url_format = 'report_images/{uid}/{timestamp}_{uuid}.jpeg'
        blob = bucket.blob(report_url_format.format(
            uid=uid,
            reporter_nickname=reporter_nickname,
            reportee_nickname=reportee_nickname,
            timestamp=pendulum.now().int_timestamp,
            uuid=uuid.uuid1())
        )
        blob.upload_from_file(report_image)
        report_image_urls.append(blob.public_url)

    report = Report(
        reporter=reporter,
        reportee=reportee,
        post=post,
        description=description,
        reported_at=reported_at,
        report_images=report_image_urls,
        is_resolved=False
    )
    report.save()

    return Response("", mimetype=mimetype)
