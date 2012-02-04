"""
    :copyright: (c) 2011 Local Projects, all rights reserved
    :license: Affero GNU GPL v3, see LICENSE for more details.
"""

import cStringIO
import traceback
import framework.util as util
import os
from framework.s3uploader import S3Uploader
from framework.log import log
from framework.controller import Controller
from framework.config import Config
from PIL import Image, ImageOps

class FileServer(object):
    """
    A generic FileServer.
    
    """
    
    def add(self, data, filename=None, make_unique=False, max_size=None, grayscale=False, mirror=True, thumb_max_size=None):
        """
        Add a file to the fileserver.  If either adding the database record for 
        the file or saving the file fails, then add will return None, and no
        modification will be made.  Otherwise, the ID of the record in the 
        database will be returned.
        
        """
        log.info("FileServer.add")
        
        # Create a unique filename
        if not filename or make_unique:
            filename = self.getUniqueFilename(filename)
        
        # Save the file to the system
        success = self.saveFile(filename, data, max_size=max_size, mirror=mirror)
        
        # Return the media_id of the file
        return filename
    
    
    def getUniqueFilename(self, filename):
        """
        Get a unique name for the file. 
        
        """
        raise NotImplementedError
    
    
    def addDbRecord(self, db, filename):
        """
        Insert a new record for a file into the given database.
        
        Arguments:
        db -- A web.py database (`web.db`) object
        app -- The name of the app (`str`)
        
        """
        try:
            id = db.insert('attachments', title=filename)
        except Exception, e:
            log.error(e)
            return None
        
        return id
    
    
    def removeDbRecord(self, db, id):
        try:
            db.query("DELETE FROM files WHERE id=$id", {'id': id})
            log.warning("--> removed id %s" % id)
            return True
        except Exception, e:
            log.error(e)
            return False
    
    
    def saveFile(self, fileid, data, **kwargs):
        """
        Save the data into a file.  Return True is file successfully saved,
        otherwise False.
        
        Override this method to save files in other places.
        
        Attributes:
        fileid -- The id from the database record that corresponds to this file
        data -- The data (string of bytes) contained in the file
        
        """
        raise NotImplementedError(("You must override the implementaion of "
                                   "saveFile for your file server.  For "
                                   "example, check out the S3FileServer."))


class S3FileServer(FileServer):
    """
    In order to use this FileServer, make sure that you have the aws section
    filled out in your conf.yaml file:
    
    aws:
        access_key_id: '<ACCESS_KEY>'
        secret_access_key: '<SECRET_KEY>'
        bucket: '<BUCKET_NAME>'
    
    """
    def __init__(self, db):
        """
        Creates an Amazon AWS S3 file server wrapper.
        
        Arguments:
        ``db``
            A ``web.db.DB`` object. This may come in handy for determining a
            unique filename for a file. Will alleviate the need to make
            additional requests to the S3 server.
        
        """
        self.db = db
        
    
    def getConfigVar(self, var_name):
        return Config.get(var_name)
    
    
    def getUniqueFilename(self, filename):
        """
        Get a unique name for the file. 
        
        """
        rows = self.db.query('''select media_id from attachments
              where type in $types''', {'types':['file','image']})
        filenames = [row.media_id for row in rows]
        
        import random
        alphanum = ('1234567890'
            'abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
        # Construct random filenames until we find one that's not in use.
        while True:
            randomizer = ''.join([random.choice(alphanum) for _ in xrange(8)])
            if '-'.join([filename, randomizer]) not in filenames:
                filename = '-'.join([randomizer, filename]) if filename else randomizer
                break
        
        return filename
    
    
    def getLocalPath(self, fileid):
        """
        Get the path to the file given by the fileid on the local file system.
        This is used only to temporarily save the file before uploading it to
        the S3 server.
        
        """
        return "%(file_path)s/%(file_id)s" % {'file_path': Config.get('media').get('file_path'),
                                             'file_id': fileid}
    
    
    def getS3Path(self, fileid):
        """
        Get the path to the file given by the fileid on the S3 server.
        
        """
        return "%(file_path)s/%(file_id)s" % {'file_path': Config.get('media').get('file_path'),
                                             'file_id': fileid}
    
    
    def saveTemporaryLocalFile(self, path, data):
        """
        Save the file on the local file system.
        This is used only to temporarily save the file before uploading it to
        the S3 server.  Creates directory if needed.
        
        """
        directory = os.path.dirname(path)
        try:
            # Attempt to create directory structure if
            # not present.
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            # Create file
            with open(path, "wb") as f:
                f.write(data)
        except Exception, e:
            log.error(e)
            return False
        
        return True
    
    
    def saveFile(self, filename, data, mirror=True, **kwargs):
        """
        Save the data into a file.  Return True is file successfully saved,
        otherwise False.
        
        Attributes:
        filename -- The id from the database record that corresponds to the file
        data -- The data (string of bytes) contained in the file
        
        """
        localpath = self.getLocalPath(filename)
        localsaved = self.saveTemporaryLocalFile(localpath, data)
        if not localsaved:
            return False
        
        isS3mirror = self.getConfigVar('media')['isS3mirror']
        s3path = self.getS3Path(filename)
        log.info("*** config = %s, mirror = %s" % (isS3mirror, mirror))
        if (isS3mirror and mirror):
            try:
                result = S3Uploader.upload(localpath, s3path)
                log.info(result)
            except Exception, e:
                tb = traceback.format_exc()
                log.error(tb)
                return False
        
        return True
        
    #
#    @classmethod
#    def cropToBox(cls, image):
#        if (image.size[0] > image.size[1]):
#            max_length = image.size[1]
#            top = 0
#            left = int(float(image.size[0] - max_length)/float(2))
#        else:
#            max_length = image.size[0]
#            top = int(float(image.size[1] - max_length)/float(2))
#            left = 0
#            
#        box = (left, top, left + max_length, top + max_length)
#        
#        return image.crop(box)
#         
#        
#    # old resize method    
#    @classmethod
#    def resizeToMax(cls, image, max_size):
#        ratio = float(max_size[0]) / float(image.size[0]) if image.size[0] > max_size[0] else float(max_size[1]) / float(image.size[1])
#        new_size = int(ratio * image.size[0]), int(ratio * image.size[1])
#        log.info("--> resizing to %sx%s" % new_size)
#        image = image.resize(new_size, Image.ANTIALIAS)     
#        return image

#    # new resize method, eholda 2011-02-12
#    @classmethod
#    def resizeToFit(cls, image, box):
#        if (image.size[0] > box[0] or image.size[1] > box[1]):
#            xratio = float(box[0]) / float(image.size[0])
#            yratio = float(box[1]) / float(image.size[1])
#        
#            ratio = xratio if xratio < yratio else yratio
#            
#            #print "--> xratio = %s, yratio = %s, ratio = %s" % (xratio, yratio, ratio)
#            
#            newsize = [int(ratio * image.size[0]), int(ratio * image.size[1])]
#        
#            log.info("*** RESIZING from %s to %s" % ([image.size[0], image.size[1]], newsize))
#            
#            return image.resize(newsize, Image.ANTIALIAS)
#        else:
#            print "--> no resize"
#            return image     

#    @classmethod
#    def remove(cls, db, app, id):
#        log.info("ImageServer.remove %s %s" % (app, id))
#        path = ImageServer.path(app, id)
#        try:
#            db.query("DELETE FROM images WHERE id=$id", {'id': id})
#            os.remove(path)
#        except Exception, e:
#            log.error(e)
#        else:
#            log.info("--> removed id %s" % id)        
#       
#    @classmethod
#    def path(cls, app, id):
#        path = "data/%s/images/%s/%s.png" % (app, str(id)[-1], id)
#        return path
#    
#    def GET(self, app=None, mode=None, target_width=None, target_height=None, id=None):
#        log.info("ImageServer.get app[%s] mode[%s] width[%s] height[%s] id[%s]" % (app, mode, target_width, target_height, id))       
#        key = "%s_%s_%s_%s_%s" % (app, mode, target_width, target_height, id)
#        image = self.cache.get(str(key))
#        if image is not None:
#            log.info("--> image [%s] is cached! yay!" % key)
#            return self.image(image)
#        image = None
#        if mode != 'bounded' and mode != 'exact':
#            return self.error("Mode not available")          
#        try:
#            record = list(Controller.get_db().query("SELECT id FROM images WHERE id=$id", {'id': id}))[0]
#        except Exception, e:
#            log.error("No image found with that ID (%s)" % e)
#        else:
#            try:
#                path = ImageServer.path(app, id)
#                log.info("--> %s" % path)
#                image = Image.open(path)                
#                found = True
#            except Exception, e:
#                log.error(e)
#        if not image:   
#            cache_image = False
#            log.info("--> showing image placeholder")
#            image = Image.open("static/img/image_placeholder.png", 'r')                
#        else:
#            cache_image = True
#        source_width = image.size[0]
#        source_height = image.size[1]                                
#        try:
#            target_width = int(target_width)
#            if target_width < 1: raise Error
#        except Exception:
#            target_width = source_width
#        try:
#            target_height = int(target_height)
#            if target_height < 1: raise Error            
#        except Exception:
#            target_height = source_height
#        source_ratio = float(source_width) / float(source_height)
#        target_ratio = float(target_width) / float(target_height)            
#        log.info("--> source %sx%s (%s)" % (source_width, source_height, source_ratio))
#        log.info("--> target %sx%s (%s)" % (target_width, target_height, target_ratio))

#        if not target_width and not target_height:
#            log.info("--> no target dimensions, showing at source dimensions")
#        elif target_width == source_width and target_height == source_height:
#            log.info("--> target matches source dimensions")
#        else:
#            if mode == 'exact':
#                if source_ratio < target_ratio:
#                    res = int(target_width), int(target_width / source_ratio)
#                    image = image.resize(res, Image.ANTIALIAS)
#                    cropoff = (image.size[1] - target_height) / 2
#                    crop = 0, cropoff, image.size[0], image.size[1] - cropoff
#                    image = image.crop(crop)
#                else:
#                    res = int(target_height * source_ratio), int(target_height)
#                    image = image.resize(res, Image.ANTIALIAS)
#                    cropoff = (image.size[0] - target_width) / 2
#                    crop = cropoff, 0, image.size[0] - cropoff, image.size[1]
#                    image = image.crop(crop)
#            else:
#                if source_ratio < target_ratio:
#                    res = int(target_height * source_ratio), int(target_height)
#                else:
#                    res = int(target_width), int(target_width / source_ratio)
#                image = image.resize(res, Image.ANTIALIAS)
#        log.info("--> result %sx%s (%s)" % (image.size[0], image.size[1], mode))
#        image = self._image_string(image)
#        if cache_image:
#            try:
#                if self.cache.add(str(key), image): # cache forever
#                    log.info("--> image cached")
#                else:
#                    log.warning("--> memcache set failed [no error]: %s" % key)
#            except Exception, e:
#                log.warning("--> memcache set failed [%s]: %s" % (e, key))
#            return self.image(image)
#        else:
#            log.info("--> placeholder image, not caching")
#            return self.temp_image(image)
#            
#    def _image_string(self, image):
#        f = cStringIO.StringIO()
#        image.save(f, "PNG")
#        f.seek(0)                    
#        return f.read()
