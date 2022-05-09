"""
API endpoints for "Audio Transcribe" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort

from sqlalchemy.orm import load_only
from sqlalchemy import func, or_, and_
from sqlalchemy.inspection import inspect

from app import db, c_abort, audiotranscribefile
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.resources.accounts.models import Account
from app.resources.audio_transcribe.models import AudioTranscribe
from app.resources.audio_transcribe.schemas import AudioTranscribeSchema, AudioTranscribeReadArgsSchema
from app.resources.audio_transcribe.helpers import delete_transcription_job, generate_vocab
from queueapp.audio_transcribe.get_transcription import transcribe_audio
from app.common.utils import delete_folder_from_s3


class AudioTranscribeAPI(AuthResource):
    """
    For creating new audio transcribe
    """

    def post(self):
        """
        Create corporate announcement
        """
        vocab_flag = False
        audio_transcribe_schema = AudioTranscribeSchema()
        # get the form data from the request
        json_data = request.form.to_dict()
        print(json_data)
        if not json_data:
            c_abort(400)

        try:
            data, errors = audio_transcribe_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            """if (g.current_user['is_admin'] is not True and
                    g.current_user['account_type'] != ACCOUNT.ACCT_CORPORATE):
                c_abort(403)"""
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            if data.acc_id:
                vocab_flag = generate_vocab(data.acc_id, 'TestAccVocab')

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        file_full_folder = data.full_folder_path(
            AudioTranscribe.root_file_folder_key)
        if 'filename' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                audiotranscribefile, request.files['filename'],
                sub_folder=sub_folder, full_folder=file_full_folder,
                detect_type=True, type_only=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'filename' in request.form:
            file_data['delete'] = []
            if request.form['filename'] == data.filename:
                file_data['delete'].append(
                    request.form['filename'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=file_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.filename = [
                        fname for fname in file_data['files']][0]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

            if data.filename:
                if vocab_flag:
                    transcribe_audio.s(True, data.row_id, vocab_flag, 'TestAccVocab').delay()
                else:
                    transcribe_audio.s(True, data.row_id, vocab_flag, 'TestAccVocab').delay()
        except HTTPException as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            raise e

        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Audio Transcription job created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def get(self, row_id):

        audio_transcribe_schema = AudioTranscribeSchema()
        model = None
        try:
            # first find model
            model = AudioTranscribe.query.get(row_id)
            if model is None:
                c_abort(404, message='BSEFeed id: %s does not exist' %
                                     str(row_id))

            result = audio_transcribe_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            model = AudioTranscribe.query.get(row_id)
            if model is None:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            if model:
                file_full_folder = model.full_folder_path(
                    AudioTranscribe.root_file_folder_key)
                ferrors = delete_folder_from_s3(file_full_folder)
                if ferrors:
                    print(ferrors)
                    return ferrors
                # response = delete_transcription_job(model, model.transcript_job_name)
                # print("transcript job delete response :", response)
            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204


class AudioTranscribeListAPI(AuthResource):
    """
    Read API for audio transcribe lists, i.e, more than 1
    """

    model_class = AudioTranscribe

    def __init__(self, *args, **kwargs):
        super(AudioTranscribeListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """

        title = filters.pop('title', None)
        email = filters.pop('email', None)
        account_name = filters.pop('account_name', None)
        query_filters, extra_query, db_projection, s_projection, order, \
        paging = self._build_query(
            filters, pfields, sort, pagination, operator,
            include_deleted=include_deleted)

        if extra_query:
            pass

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.join(
            Account, Account.row_id == AudioTranscribe.acc_id, isouter=True)

        if email and title and account_name:
            query = query.filter(
                or_(func.lower(AudioTranscribe.title).like('%' + title.lower() + '%'),
                    func.lower(AudioTranscribe.email).like('%' + email.lower() + '%'),
                    func.lower(Account.account_name).like('%' + account_name.lower() + '%')))

        if sort:
            for col in sort['sort_by']:
                if col == 'title':
                    mapper = inspect(AudioTranscribe)
                    col = 'title'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())
                if col == 'created_date':
                    mapper = inspect(AudioTranscribe)
                    col = 'created_date'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())
                if col == 'account_name':
                    mapper = inspect(Account)
                    col = 'account_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())


        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            AudioTranscribeReadArgsSchema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AudioTranscribe),
                                 operator)
            # making a copy of the main output schema
            audio_transcribe_schema = AudioTranscribeSchema()
            # comment_schema = AudioTranscribeSchema(
            #     exclude=AudioTranscribeSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                audio_transcribe_schema = AudioTranscribeSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Market performance found')
            result = audio_transcribe_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200